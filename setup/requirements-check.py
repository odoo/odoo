#!/usr/bin/env python
"""
Checks versions from the requirements files, either against a Debian/Ubuntu specific distribution
, against a windows python version or against accessible locally installed versions.
"""

import argparse
import gzip
import itertools
import json
import pkg_resources
import re

from abc import ABC, abstractmethod
from pathlib import Path
from urllib.request import urlopen
from sys import stdout, stderr
from typing import Optional, Tuple


def print_table(table, widthes):
    # format table
    for row in table:
        stdout.write('| ')
        for cell, width in zip(row, widthes):
            stdout.write(f'{str(cell):<{width}} | ')
        stdout.write('\n')


Version = Tuple[int, ...]
def parse_version(vstring: str) -> Optional[Version]:
    if not vstring:
        return None
    return tuple(map(int, vstring.split('.')))


# shared beween debian and ubuntu
SPECIAL = {
    'pytz': 'tz',
    'libsass': 'libsass-python',
}
def unfuck(s: str) -> str:
    """ Try to strip the garbage from the version string, just remove everything
    following the first `+`, `~` or `-`
    """
    return re.match(r'''
        (?:\d+:)? # debian crud prefix
        (.*?) # the shit we actually want
        (?:~|\+|-|\.dfsg)
        .*
    ''', s, flags=re.VERBOSE)[1]


class Distribution(ABC):
    def __init__(self, release):
        self._release = release

    @abstractmethod
    def get_version(self, package: str) -> Optional[Version]:
        ...

    def __str__(self):
        return f'{type(self).__name__.lower()} {self._release}'

    @classmethod
    def get(cls, name):
        try:
            return next(
                c
                for c in cls.__subclasses__()
                if c.__name__.lower() == name
            )
        except StopIteration:
            raise ValueError(f"Unknown distribution {name!r}")

    def get_python_version(self):
        return '.'.join(map(str, self.get_version('python3-defaults')[:2]))


class Debian(Distribution):
    def get_version(self, package):
        """ Try to find which version of ``package`` is in Debian release {release}
        """
        package = SPECIAL.get(package, package)
        # try the python prefix first: some packages have a native of foreign $X and
        # either the bindings or a python equivalent at python-X, or just a name
        # collision
        for prefix in ['python-', '']:
            res = json.load(urlopen(f'https://sources.debian.org/api/src/{prefix}{package}'))
            if res.get('error') is None:
                break
        if res.get('error'):
            return

        return next(
            parse_version(unfuck(distr['version']))
            for distr in res['versions']
            if distr['area'] == 'main'
            if self._release in distr['suites']
        )


class Ubuntu(Distribution):
    """ Ubuntu doesn't have an API, instead it has a huge text file
    """
    def __init__(self, release):
        super().__init__(release)

        self._packages = {}
        # ideally we should request the proper Content-Encoding but PUC
        # apparently does not care, and returns a somewhat funky
        # content-encoding (x-gzip) anyway
        data = gzip.open(
            urlopen(f'https://packages.ubuntu.com/source/{release}/allpackages?format=txt.gz'),
            mode='rt', encoding='utf-8'
        )
        for line in itertools.islice(data, 6, None): # first 6 lines is garbage header
            # ignore the restricted, security, universe, multiverse tags
            m = re.match(r'(\S+) \(([^)]+)\)', line.strip())
            assert m, f"invalid line {line.strip()!r}"
            self._packages[m[1]] = m[2]

    def get_version(self, package):
        package = SPECIAL.get(package, package)
        for prefix in ['python3-', 'python-', '']:
            v = self._packages.get(f'{prefix}{package}')
            if v:
                return parse_version(unfuck(v))
        return None


class Windows(Distribution):
    """Windows `Distribution` is a special case as it does not provide a Python package.
    The `get_python_version` method simply returns the python verion chosen in the release
    at object instanciation.

    e.g.: when release is `amd_64-cp37` it will return '3.7' as python version.

    Also, when searching for a suitable version for a package, the `get_version` method
    searches on pypi for the latest version of the package that provides a binary wheel that
    match the platform and the python version or a simple wheel when the package is pure python.
    :param release: The release param is used to specify the windows architecture and the python version.
    :type release: str
    """

    def __init__(self, release):
        super().__init__(release)
        assert re.search(r'(win32|win_amd64)-cp\d+', release), "Invalid windows distribution speicification"
        self.winver, self.pyver = release.split('-')

    def get_python_version(self):
        return f'{self.pyver[2]}.{self.pyver[3]}'

    def get_version(self, package):

        def info_filter(info):
            if info['packagetype'] == 'bdist_wheel':
                if (info['python_version'] == self.pyver and self.winver in info['filename']) or '-any.whl' in info['filename']:
                    return True
            return False

        res = json.load(urlopen(f'https://pypi.org/pypi/{package}/json'))
        candidates = []
        for version, infos in res['releases'].items():
            if any(filter(info_filter, infos)):
                candidates.append(version)
        return candidates and sorted(candidates)[0].split('.') or []


def check_distros(args):
    """ Checks versions from the requirements files against distribution-provided
    versions, taking distribution's Python version in account e.g. if checking
    against a release which bundles Python 3.5, checks the 3.5 version of
    requirements.

    Note that for the `windows` distribution, as no python is provided by the
    dsitribution, it has to be specified iby the user in the release par of the
    argument.
    e.g.: `windows:win_amd64-cp37`, here the `cp37` means python 3.7.

    * only shows requirements for which at least one release diverges from the
    matching requirements version
    * empty cells mean that specific release matches its requirement (happens when
    checking multiple releases: one of the other releases may mismatch the its
    requirements necessating showing the row)
    """
    checkers = [
        Distribution.get(distro)(release)
        for version in args.release
        for (distro, release) in [version.split(':')]
    ]

    stderr.write(f"Fetch Python versions...\n")
    pyvers = [checker.get_python_version() for checker in checkers]

    uniq = sorted(v for v in set(pyvers))
    table = [
        ['']
        + [f'req {v}' for v in uniq]
        + [f'{checker._release} ({version})' for checker, version in zip(checkers, pyvers)]
    ]

    with ((Path.cwd() / __file__).parent.parent / 'requirements.txt').open() as req_file:
        reqs = [r for r in pkg_resources.parse_requirements(req_file)]

    tot = len(reqs) * len(checkers)

    def progress(n=iter(range(tot + 1))):
        stderr.write(f"\rFetch requirements: {next(n)} / {tot}")

    progress()
    for requirement in reqs:
        row = [requirement.project_name]
        byver = {}
        for pyver in uniq:
            environment = {'python_version': pyver, 'sys_platform': 'linux'}
            if requirement.marker and not requirement.marker.evaluate(environment=environment):
                continue
            byver[pyver] = requirement.specifier
            row.append(str(requirement.specifier))

        if not byver:
            for _ in checkers:
                progress()
            continue

        mismatch = False
        for i, checker in enumerate(checkers):
            req_specifier = byver.get(pyvers[i], '')
            check_version_string = '.'.join(map(str, checker.get_version(requirement.name.lower()) or ['<missing>']))
            progress()
            try:
                check_version = pkg_resources.packaging.version.Version(check_version_string)
            except pkg_resources.packaging.version.InvalidVersion:
                row.append(check_version_string)
                mismatch = True
            else:
                if check_version_string not in req_specifier:
                    mismatch = True
                    row.append(check_version_string)
                else:
                    row.append('')

        # only show row if one of the items diverges from requirement
        if mismatch:
            table.append(row)
    stderr.write('\n')
    # evaluate width of columns
    sizes = [0] * (len(checkers) + len(uniq) + 1)
    for row in table:
        sizes = [
            max(s, len(cell))
            for s, cell in zip(sizes, row)
        ]

    print_table(table, sizes)


def location_to_source(distrib):
    """ returns a string that describes the source of the Python package based on its location
    :param distrib: a pkg_resources.Distribution instance
    :rtype: string
    """
    naive_kw = {
        'Debian': r'/usr/lib/.+/dist-packages',
        'pip global': r'/usr/local/lib/.+dist-packages',
        'Pyenv': r'pyenv',
        'User': str(Path.home())}
    for source, keyword in naive_kw.items():
        if re.search(keyword, distrib.location):
            return source
    return 'Other'


def check_local(args):
    results = [('Project', 'Expected', 'Installed', 'Source', 'Location')]
    with ((Path.cwd() / __file__).parent.parent / 'requirements.txt').open() as req_file:
        for requirement in pkg_resources.parse_requirements(req_file):
            if requirement.marker and not requirement.marker.evaluate():
                # skipping requirement that marker does not match
                continue
            try:
                distrib = pkg_resources.get_distribution(requirement)
            except pkg_resources.DistributionNotFound:
                results.append((requirement.project_name, requirement.specifier, 'Not found', '--', '--'))
            except pkg_resources.VersionConflict as e:
                results.append((requirement.project_name, requirement.specifier, e.dist.version, location_to_source(e.dist), e.dist.location))
            else:
                results.append((requirement.project_name, requirement.specifier, '✔', location_to_source(distrib), distrib.location))

    widthes = [0] * 5
    for row in results:
        for i, c in enumerate(row):
            widthes[i] = max(widthes[i], len(str(c)))

    print_table(results, widthes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    def print_help(args):
        # hack to set a default func that prints help when no command is chosen
        parser.print_help()

    parser.set_defaults(func=print_help)

    subparsers = parser.add_subparsers()

    parser_distro_check = subparsers.add_parser('distro', help='Check requirements against distributions')
    parser_distro_check.add_argument(
        'release', nargs='+',
        help="Release to check against, should use the format '{distro}:{release}' e.g. 'debian:sid'"
    )
    parser_distro_check.set_defaults(func=check_distros)

    parser_local_check = subparsers.add_parser('local', help='Check requirements against local modules')
    parser_local_check.set_defaults(func=check_local)

    args = parser.parse_args()
    args.func(args)
