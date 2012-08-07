#!/usr/bin/python

import argparse
import ConfigParser
import glob
import os.path
import subprocess
import sys


def handle_project(config, state, workdir, repo, series, keyid, name):
    print("Processing %s" % (name,))

    workdir = '%s/%s' % (workdir, name)

    if not os.path.exists(workdir):
        os.makedirs(workdir)

    codedir = '%s/code' % workdir
    packagingdir = '%s/packaging' % workdir

    available_code_revision = lookup_revision(config.get(name, 'code'))
    available_packaging_revision = lookup_revision(config.get(name,
                                                              'packaging'))


    if (not state.has_section(name)
        or state.get(name, 'code_revision') != available_code_revision
        or state.get(name, 'packaging_revision') != available_packaging_revision):

        checkout_code(config.get(name, 'code'),
                      codedir, available_code_revision)
        checkout_code(config.get(name, 'packaging'),
                      packagingdir, available_packaging_revision)

        if not state.has_section(name):
            state.add_section(name)
            our_version = 1
        else:
            our_version = state.getint(name, 'our_version') + 1

        derived_upstream_version = produce_tarball(codedir, name, our_version)

        pkg_version = stitch_together(packagingdir,
                                      derived_upstream_version,
                                      available_packaging_revision,
                                      available_code_revision,
                                      series, keyid)

        if repo:
            print ('dput', repo,
                     '%s/%s_%s_source.changes' % (workdir, name, pkg_version))

        state.set(name, 'code_revision', available_code_revision)
        state.set(name, 'packaging_revision', available_packaging_revision)
        state.set(name, 'our_version', '%s' % (our_version,))


def produce_tarball(codedir, project, our_version):
    for f in glob.glob('%s/dist/*' % (codedir,)):
        os.unlink(f)

    run_cmd('python', 'setup.py', 'sdist', cwd=codedir)
    tarball = glob.glob('%s/dist/*' % (codedir,))[0]
    base_upstream_version = tarball.split('/')[-1].split('-')[1][:-(len('.tar.gz'))]
    derived_upstream_version = '%s+stable+%d' % (base_upstream_version, our_version)
    os.rename(tarball,
              '%s/../%s_%s.orig.tar.gz' % (codedir,
                                           project,
                                           derived_upstream_version))
    return derived_upstream_version


def stitch_together(packagingdir,
                    derived_upstream_version,
                    packaging_revision, code_revision, series, keyid):
    pkg_version = '%s-0~%s1' % (derived_upstream_version, series)
    run_cmd('dch', '-b',
                   '--force-distribution',
                   '-v', pkg_version,
                   'Automated PPA build. Code revision: %s. '
                   'Packaging revision: %s.' % (code_revision,
                                                packaging_revision),
                   '-D', series,
            cwd=packagingdir)
    run_cmd('bzr', 'bd', '-S',
            '--orig-dir', '..',
            '--result-dir', '..',
            '--builder=dpkg-buildpackage -k%s' % (keyid,),
            cwd=packagingdir)
    return pkg_version


def lookup_revision(url):
    print ("Looking up current revision of %s" % (url,))
    vcstype = guess_type(url)

    if vcstype == 'bzr':
        out = run_cmd('bzr', 'revision-info', '-d', url)
        return out.split('\n')[0].split(' ')[1]

    if vcstype == 'git':
        if '#' in url:
            url, branch = url.split('#')
        else:
            branch = 'master'
        out = run_cmd('git', 'ls-remote', url, branch)
        return out.split('\n')[0].split('\t')[0]


def checkout_code(url, destdir, revision):
    print ("Checking out revision %s of %s" % (revision, url))
    vcstype = guess_type(url)

    if vcstype == 'bzr':
        if os.path.exists(destdir):
            run_cmd('bzr', 'pull', '-r', revision, '-d', destdir, url)
            run_cmd('bzr', 'revert', '-r', revision, cwd=destdir)
            run_cmd('bzr', 'clean-tree', '--unknown', '--detritus',
                                         '--ignored', '--force',
                    cwd=destdir)
        else:
            run_cmd('bzr', 'branch', '-r', revision, url, destdir)
    elif vcstype == 'git':
        url = url.split('#')[0]
        if os.path.exists(destdir):
            run_cmd('git', 'fetch', url, cwd=destdir)
            run_cmd('git', 'reset', '--hard', revision, cwd=destdir)
            run_cmd('git', 'clean', '-dfx', cwd=destdir)
        else:
            run_cmd('git', 'clone', url, destdir)
            run_cmd('git', 'reset', '--hard', revision, cwd=destdir)


def run_cmd(*args, **kwargs):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        raise Exception('Failure running %r' % (args,))
    return stdout


def guess_type(url):
    if 'launchpad' in url:
        return 'bzr'
    if 'github' in url:
        return 'git'
    raise Exception('No idea what to do with %r' % url)


def main(args=sys.argv):
    argparser = argparse.ArgumentParser(description='Build source packages')
    argparser.add_argument('config', help="config file")
    argparser.add_argument('state', help="state file")
    argparser.add_argument('workdir', help="working directory")
    argparser.add_argument('series', help="distro series (e.g. precise)")
    argparser.add_argument('keyid', help="Key ID")
    argparser.add_argument('--repo', help="dput destination")
    args = argparser.parse_args()

    if not os.path.exists(args.config):
        argparser.error('No such file: %r' % args.config)

    config = ConfigParser.SafeConfigParser()
    config.read(args.config)

    state = ConfigParser.SafeConfigParser()
    state.read(args.state)

    for section in config.sections():
        handle_project(config, state, args.workdir, args.repo, args.series,
                       args.keyid, section)

    with open(args.state, 'w') as statefile:
        state.write(statefile)

if __name__ == '__main__':
    sys.exit(not main())
