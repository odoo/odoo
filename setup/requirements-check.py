#!/usr/bin/env python

"""
Checks versions from the requirements files against distribution-provided
versions, taking distribution's Python version in account e.g. if checking
against a release which bundles Python 3.5, checks the 3.5 version of
requirements.

* only shows requirements for which at least one release diverges from the
  matching requirements version
* empty or green cells mean that specific release matches its requirement (happens when
  checking multiple releases: one of the other releases may mismatch the its
  requirements necessating showing the row)

This script was heavily reworked but is not in a final version:
TODO:
- add legends
- better management of cache
- add meta info on cells (mainly to genearte a better html report)
    - warn/ko reason
    - wheel + link
    - original debian package name + link
    ...

"""

import argparse
import gzip
import itertools
import json
import os
import re
import shutil
import tempfile

try:
    import ansitoimg
except ImportError:
    ansitoimg = None

from abc import ABC, abstractmethod
from pathlib import Path
from sys import stderr, stdout
from typing import Dict, List, Optional, Tuple
from urllib.request import HTTPError
from urllib.request import urlopen as _urlopen

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.tags import mac_platforms  # noqa: PLC2701
from packaging.utils import canonicalize_name

from pip._internal.index.package_finder import (
    LinkEvaluator,  # noqa: PLC2701
)
from pip._internal.models.link import Link  # noqa: PLC2701
from pip._internal.models.target_python import TargetPython  # noqa: PLC2701

Version = Tuple[int, ...]

# shared beween debian and ubuntu
SPECIAL = {
    'pytz': 'tz',
    'libsass': 'libsass-python',
}
SUPPORTED_FORMATS = ('txt', 'ansi', 'svg', 'html', 'json')
PLATFORM_CODES = ('linux', 'win32', 'darwin')
PLATFORM_NAMES = ('Linux', 'Win', 'OSX')


def urlopen(url):
    file_name = "".join(c if c.isalnum() else '_' for c in url)
    os.makedirs('/tmp/package_versions_cache/', exist_ok=True)
    file_path = f'/tmp/package_versions_cache/{file_name}'
    if not os.path.isfile(file_path):
        response = _urlopen(url)
        with open(file_path, 'wb') as fw:
            fw.write(response.read())
    return open(file_path, 'rb')   # noqa: SIM115


def parse_version(vstring: str) -> Optional[Version]:
    if not vstring:
        return None
    return tuple(map(int, vstring.split('.')))


def cleanup_debian_version(s: str) -> str:
    """ Try to strip the garbage from the version string, just remove everything
    following the first `+`, `~` or `-`
    """
    return re.match(r'''
        (?:\d+:)? # debian crud prefix
        (.*?) # the shit we actually want
        (?:~|\+|-|\.dfsg)
        .*
    ''', s, flags=re.VERBOSE)[1]


class PipPackage:
    def __init__(self, name):
        self.name = name
        infos = json.load(urlopen(f'https://pypi.org/pypi/{name}/json'))
        self.info = infos['info']
        self.last_serial = infos['last_serial']
        self.releases = infos['releases']
        self.urls = infos['urls']
        self.vulnerabilities = infos['vulnerabilities']

    def has_wheel_for(self, version, python_version, platform):
        if version is None:
            return (False, False, False)
        py_version_info = python_version.split('.')
        if len(py_version_info) == 2:
            py_version_info = (py_version_info[0], py_version_info[1], 0)
        releases = self.releases
        has_wheel_for_version = False
        has_any_wheel = False
        has_wheel_in_another_version = False
        platforms = None
        if platform == 'darwin':
            platforms = list(mac_platforms((15, 0), 'x86_64'))
        elif platform == 'win32':
            platforms = ['win32', 'win-amd64']
        else:
            assert platform == 'linux'

        target_python = TargetPython(
            platforms=platforms,
            py_version_info=py_version_info,
            abis=None,
            implementation=None,
        )
        le = LinkEvaluator(
            project_name=self.name,
            canonical_name=canonicalize_name(self.name),
            formats={"binary", "source"},
            target_python=target_python,
            allow_yanked=True,
            ignore_requires_python=False,
        )
        for release in releases[version]:
            if release['filename'].endswith('.whl'):
                has_any_wheel = True
            is_candidate, _result = le.evaluate_link(Link(
                comes_from=None,
                url=release['url'],
                requires_python=release['requires_python'],
                yanked_reason=release['yanked_reason'],
            ))
            if is_candidate:
                if release['filename'].endswith('.whl'):
                    has_wheel_for_version = has_wheel_in_another_version = True
                break

        if not has_wheel_for_version and has_any_wheel:
            # TODO, we should prefer a version matching the one from a distro
            for rel_version, rel in releases.items():
                for release in rel:
                    if not release['filename'].endswith('.whl'):
                        continue
                    if any(not s.isdigit() for s in rel_version.split('.')) or parse_version(rel_version) <= parse_version(version):
                        continue
                    is_candidate, _result = le.evaluate_link(Link(
                        comes_from=None,
                        url=release['url'],
                        requires_python=release['requires_python'],
                        yanked_reason=release['yanked_reason'],
                    ))
                    if is_candidate:
                        has_wheel_in_another_version = True
                        stderr.write(f'WARNING: Wheel found for {self.name} ({python_version} {platform}) in {rel_version}\n')
                        return (has_wheel_for_version, has_any_wheel, has_wheel_in_another_version)

        return (has_wheel_for_version, has_any_wheel, has_wheel_in_another_version)


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
            msg = f"Unknown distribution {name!r}"
            raise ValueError(msg)


class Debian(Distribution):
    def get_version(self, package):
        """ Try to find which version of ``package`` is in Debian release {release}
        """
        package = SPECIAL.get(package, package)
        # try the python prefix first: some packages have a native of foreign $X and
        # either the bindings or a python equivalent at python-X, or just a name
        # collision
        prefixes = ['python-', '']
        if package.startswith('python'):
            prefixes = ['']
        for prefix in prefixes:
            try:
                res = json.load(urlopen(f'https://sources.debian.org/api/src/{prefix}{package}/'))
            except HTTPError:
                return 'failed'
            if res.get('error') is None:
                break
        if res.get('error'):
            return

        try:
            return next(
                parse_version(cleanup_debian_version(distr['version']))
                for distr in res['versions']
                if distr['area'] == 'main'
                if self._release.lower() in distr['suites']
            )
        except StopIteration:
            return


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
            mode='rt', encoding='utf-8',
        )
        for line in itertools.islice(data, 6, None):  # first 6 lines is garbage header
            # ignore the restricted, security, universe, multiverse tags
            m = re.match(r'(\S+) \(([^)]+)\)', line.strip())
            assert m, f"invalid line {line.strip()!r}"
            self._packages[m[1]] = m[2]

    def get_version(self, package):
        package = SPECIAL.get(package, package)
        for prefix in ['python3-', 'python-', '']:
            v = self._packages.get(f'{prefix}{package}')
            if v:
                return parse_version(cleanup_debian_version(v))
        return None


def _strip_comment(line):
    return line.split('#', 1)[0].strip()


def parse_requirements(reqpath: Path) -> Dict[str, List[Tuple[str, Marker]]]:
    """ Parses a requirement file to a dict of {package: [(version, markers)]}

    The env markers express *whether* that specific dep applies.
    """
    reqs = {}
    with reqpath.open('r', encoding='utf-8') as f:
        for req_line in f:
            req_line = _strip_comment(req_line)
            if not req_line:
                continue
            requirement = Requirement(req_line)
            version = None
            if requirement.specifier:
                if len(requirement.specifier) > 1:
                    raise NotImplementedError('multi spec not supported yet')
                version = next(iter(requirement.specifier)).version
            reqs.setdefault(requirement.name, []).append((version, requirement.marker))
    return reqs


def ok(text):
    return f'\033[92m{text}\033[39m'


def em(text):
    return f'\033[94m{text}\033[39m'


def warn(text):
    return f'\033[93m{text}\033[39m'


def ko(text):
    return f'\033[91m{text}\033[39m'


def default(text):
    return text


def main(args):
    checkers = [
        Distribution.get(distro)(release)
        for version in args.release
        for (distro, release) in [version.split(':')]
    ]

    stderr.write("Fetch Python versions...\n")
    pyvers = [
        '.'.join(map(str, checker.get_version('python3-defaults')[:2]))
        for checker in checkers
    ]

    uniq = sorted(set(pyvers), key=parse_version)
    platforms = PLATFORM_NAMES if args.check_pypi else PLATFORM_NAMES[:1]
    platform_codes = PLATFORM_CODES if args.check_pypi else PLATFORM_CODES[:1]
    platform_headers = ['']
    python_headers = ['']
    table = [platform_headers, python_headers]
    # requirements headers
    for v in uniq:
        for p in platforms:
            platform_headers.append(p)
            python_headers.append(v)

    # distro headers
    for checker, version in zip(checkers, pyvers):
        platform_headers.append(checker._release[:5])
        python_headers.append(version)

    reqs = parse_requirements((Path.cwd() / __file__).parent.parent / 'requirements.txt')
    if args.filter:
        reqs = {r: o for r, o in reqs.items() if any(f in r for f in args.filter.split(','))}

    for req, options in reqs.items():
        if args.check_pypi:
            pip_infos = PipPackage(req)
        row = [req]
        seps = [' || ']
        byver = {}
        for pyver in uniq:
            # FIXME: when multiple options apply, check which pip uses
            #        (first-matching. best-matching, latest, ...)
            seps[-1] = ' || '
            for platform in platform_codes:
                platform_version = 'none'
                for version, markers in options:
                    if not markers or markers.evaluate({
                        'python_version': pyver,
                        'sys_platform': platform,
                    }):
                        if platform == 'linux':
                            byver[pyver] = version
                        platform_version = version
                        break
                deco = None
                if args.check_pypi:
                    if platform_version == 'none':
                        deco = 'ok'
                    else:
                        has_wheel_for_version, has_any_wheel, has_wheel_in_another_version = pip_infos.has_wheel_for(platform_version, pyver, platform)
                        if has_wheel_for_version:
                            deco = 'ok'
                        elif has_wheel_in_another_version:
                            deco = 'ko'
                        elif has_any_wheel:
                            deco = 'warn'
                    if deco in ("ok", None):
                        if byver.get(pyver, 'none') != platform_version:
                            deco = 'em'
                req_ver = platform_version or 'any'
                row.append((req_ver, deco))
                seps.append(' | ')

        seps[-1] = ' |#| '
        # this requirement doesn't apply, ignore
        if not byver and not args.all:
            continue

        for i, c in enumerate(checkers):
            req_version = byver.get(pyvers[i], 'none') or 'any'
            check_version = '.'.join(map(str, c.get_version(req.lower()) or [])) or None
            if req_version != check_version:
                deco = 'ko'
                if req_version == 'none':
                    deco = 'ok'
                elif req_version == 'any':
                    if check_version is None:
                        deco = 'ok'
                elif check_version is None:
                    deco = 'ko'
                elif parse_version(req_version) >= parse_version(check_version):
                    deco = 'warn'
                row.append((check_version or '</>', deco))
            elif args.all:
                row.append((check_version or '</>', 'ok'))
            else:
                row.append('')
            seps.append(' |#|  ')
        table.append(row)

    seps[-1] = ' '  # remove last column separator

    stderr.write('\n')

    # evaluate width of columns
    sizes = [0] * len(table[0])
    for row in table:
        sizes = [
            max(s, len(cell[0] if isinstance(cell, tuple) else cell))
            for s, cell in zip(sizes, row)
        ]

    output_format = 'ansi'
    if args.format:
        output_format = args.format
        assert format in SUPPORTED_FORMATS
    elif args.output:
        output_format = 'txt'
        ext = args.output.split('.')[-1]
        if ext in SUPPORTED_FORMATS:
            output_format = ext

    if output_format == 'json':
        output = json.dumps(table)
    else:
        output = ''
        # format table
        for row in table:
            output += ' '
            for cell, width, sep in zip(row, sizes, seps):
                cell_content = cell
                deco = default
                if isinstance(cell, tuple):
                    cell_content, level = cell
                    if output_format == 'txt' or level is None:
                        deco = default
                    elif level == 'ok':
                        deco = ok
                    elif level == 'em':
                        deco = em
                    elif level == 'warn':
                        deco = warn
                    else:
                        deco = ko
                output += deco(f'{cell_content:<{width}}') + sep
            output += '\n'

    if output_format in ('svg', 'html'):
        if not ansitoimg:
            output_format = 'ansi'
            stderr.write(f'Missing ansitoimg for {output_format} format, switching to ansi')
        else:
            convert = ansitoimg.ansiToSVG
            if output_format == 'html':
                convert = ansitoimg.ansiToHTML
            with tempfile.NamedTemporaryFile() as tmp:
                convert(output, tmp.name, width=(sum(sizes) + sum(len(sep) for sep in seps)), title='requirements-check.py')
                output = tmp.read().decode()
                # remove mac like bullets
                output = output.replace('''<g transform="translate(26,22)">
            <circle cx="0" cy="0" r="7" fill="#ff5f57"/>
            <circle cx="22" cy="0" r="7" fill="#febc2e"/>
            <circle cx="44" cy="0" r="7" fill="#28c840"/>
            </g>''', "")  #

    if args.output:
        with open(args.output, 'w', encoding='utf8') as f:
            f.write(output)
    else:
        stdout.write(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'release', nargs='+',
        help="Release to check against, should use the format '{distro}:{release}' e.g. 'debian:sid'"
    )
    parser.add_argument(
        '-a', '--all', action="store_true",
        help="Display all requirements even if it matches",
    )
    parser.add_argument(
        '-o', '--output', help="output path",
    )
    parser.add_argument(
        '-f', '--format', help=f"Supported format: {', '.join(SUPPORTED_FORMATS)}",
    )
    parser.add_argument(
        '--update-cache', action="store_true",
        help="Ignore the existing package version cache and update them",
    )
    parser.add_argument(
        '--check-pypi', action="store_true",
        help="Check wheel packages",
    )
    parser.add_argument(
        '--filter',
        help="Comma sepaated list of package to check",
    )

    args = parser.parse_args()
    if args.update_cache:
        shutil.rmtree('/tmp/package_versions_cache/')
    main(args)
