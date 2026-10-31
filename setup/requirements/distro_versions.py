#!/usr/bin/env python3
"""
Fetch, for each supported python version, the version of every external
python dependency declared in Odoo manifests (identified by its apt binary
package name) as packaged by the corresponding Debian/Ubuntu release, and
write the result as JSON next to this script (distro_versions.json by
default).

Uses each distro's madison service (one batched query per release): it
resolves an exact binary package name in an exact release directly, so no
name-guessing or full-archive download is needed.

Always re-fetches everything on each call (no incremental/skip-if-present
logic), so newly declared requirements are picked up next time this is run.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen

from packaging.version import parse, InvalidVersion

from manifests import get_all_requirements

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from odoo.release import MIN_PY_VERSION, MAX_PY_VERSION

Version = tuple[int, ...]

RELEASE_PER_VERSION = {
    (3, 12): ('ubuntu', 'noble'),
    (3, 13): ('debian', 'trixie'),
    (3, 14): ('ubuntu', 'resolute'),
}

all_versions = list(RELEASE_PER_VERSION)
assert all_versions[0] == MIN_PY_VERSION
assert all_versions[-1] == MAX_PY_VERSION

VERSIONS_FILE = Path(__file__).resolve().parent / 'distro_versions.json'


def parse_version(vstring: str) -> Version | None:
    try:
        return parse(vstring).release
    except InvalidVersion:
        return None


def cleanup_debian_version(s: str) -> str:
    """ Try to strip the garbage from the version string, just remove everything
    following the first `+`, `~` or `-`
    """
    return re.match(r'''
        (?:\d+:)? # debian crud prefix
        (.*?) # the part we actually want
        (?:~|\+|-|\.dfsg)
        .*
    ''', s, flags=re.VERBOSE)[1]


def fetch_debian_versions(release: str, packages: list[str]) -> dict[str, str]:
    url = f"https://api.ftp-master.debian.org/madison?package={'+'.join(packages)}&s={release}&f=json"
    print(f'Fetching {len(packages)} package versions from Debian {release}...')
    with urlopen(url) as response:
        data = json.load(response)
    result = {}
    for entry in data:
        for name, by_suite in entry.items():
            for versions_by_string in by_suite.values():
                result[name] = next(iter(versions_by_string))
    return result


def fetch_ubuntu_versions(release: str, packages: list[str]) -> dict[str, str]:
    url = f"https://ubuntu-archive-team.ubuntu.com/madison.cgi?package={'+'.join(packages)}&a=&c=&s={release}&text=on"
    print(f'Fetching {len(packages)} package versions from Ubuntu {release}...')
    with urlopen(url) as response:
        text = response.read().decode('utf-8')
    result = {}
    for line in text.splitlines():
        parts = [part.strip() for part in line.split('|')]
        if len(parts) >= 2 and parts[0]:
            result[parts[0]] = parts[1]
    return result


FETCHERS = {'debian': fetch_debian_versions, 'ubuntu': fetch_ubuntu_versions}


def fetch_all_versions(packages: list[str], release_per_version=RELEASE_PER_VERSION) -> dict[str, dict[str, str | None]]:
    versions = {}
    for python_version, (distro, release) in release_per_version.items():
        python_version_str = '.'.join(map(str, python_version))
        if distro == 'debian':
            raw_versions = fetch_debian_versions(release, packages)
        else:
            raw_versions = fetch_ubuntu_versions(release, packages)
        versions[python_version_str] = {}
        for package in packages:
            raw_version = raw_versions.get(package)
            version = parse_version(cleanup_debian_version(raw_version)) if raw_version else None
            versions[python_version_str][package] = '.'.join(map(str, version)) if version else None
    return versions


def main(args):
    requirements = get_all_requirements(args.addons_path)
    packages = set()
    for req in requirements:
        if req.get('apt'):
            packages.update(name.strip() for name in req['apt'].split('|'))
    versions = fetch_all_versions(sorted(packages))

    output_path = Path(args.output) if args.output else VERSIONS_FILE
    with output_path.open('w', encoding='utf8') as f:
        json.dump(versions, f, indent=2, sort_keys=True)
        f.write('\n')
    print(f'Wrote {output_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--addons-path', nargs='+', required=True,
        help="List of addons path to scan for requirements",
    )
    parser.add_argument(
        '-o', '--output', help="Output json path (default: next to this script)",
    )
    args = parser.parse_args()
    main(args)
