Build packages from $VCS + packaging

Polls a set of repositories for changes. If any are found, a package is built by pulling from VCS, building a tarball (using "python setup.py"), and applying packaging from bzr (using "bzr builddeb").

Invoke like:

  $ ./poll-build-upload.py --repo cisco:sorhanse config state workdir precise E8BDA4E3

cisco:sorhanse:
    The dput target where packages will be pushed

config:
    A configuration file (see the config file in the repo for an
    example)

state:
    A state file where we keep track of last seen revision id's and the
    version numbers we've used. Don't delete this!

workdir:
    A directory we use to build packages etc. You can delete this at
    will, but keeping it around saves some time when updates are found.
    Note: The polling process does not involve cloning anything, so
    not keeping the workdir around isn't that big of a deal.

precise:
    The Ubuntu series for which we're building packages.

E8BDA4E3:
    The GPG key we'll be using to sign the packages.

Note:
For the cisco:XXX dput target to work, copy the contents of dput.cf
into your ~/.dput.cf
