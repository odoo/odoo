#!/usr/bin/env python3

"""
Generate a requirements.txt, a debian/control Depends list, or a raw json
dump of the python external_dependencies declared across Odoo manifests,
pinned against the version packaged by the distro release matching each
supported python version.

Version data is read from distro_versions.json (next to this script, see
distro_versions.py) if present; otherwise it falls back to live Debian/Ubuntu
lookups.
"""

import argparse
import json
import sys

from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import parse, InvalidVersion

from manifests import get_all_requirements
from distro_versions import VERSIONS_FILE, RELEASE_PER_VERSION as release_per_version, fetch_all_versions

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from odoo.release import MAIN_PY_VERSION

Version = tuple[int, ...]

PLATFORM_CODES = ('linux', 'win32', 'darwin')
PLATFORM_NAMES = ('Linux', 'Win', 'OSX')


def parse_version(vstring: str) -> Version | None:
    try:
        return parse(vstring).release
    except InvalidVersion:
        return None


def _apt_name(requirement_spec):
    """The apt field can be a debian/control-style 'a | b' alternative list; the
    first name is the one that matches this requirement's own pypi package.
    """
    apt = requirement_spec.get('apt')
    return apt.split('|')[0].strip() if apt else None


def _is_wanted(requirement_spec, include_test, include_optional):
    return (not requirement_spec.get('test') or include_test) and (not requirement_spec.get('optional') or include_optional)


def generate_requirements(
    addons_path,
    mode='requirement',
    python_versions=None,
    platforms=None,
    modules=None,
    ignore_security=False,
    without_apt=False,
    include_test=False,
    include_optional=False,
    precomputed_versions=None,
):
    all_python_versions = list(release_per_version)

    if mode == 'debian':
        if not python_versions:
            requested_python_versions = [MAIN_PY_VERSION]
        elif len(python_versions) == 1 and python_versions != ['all']:
            requested_python_versions = [tuple(map(int, python_versions[0].split('.')))]
        else:
            sys.exit('--mode debian only supports a single --python-versions value')
    elif not python_versions:
        requested_python_versions = [tuple(sys.version_info[:2])]
    elif python_versions == ['all']:
        requested_python_versions = all_python_versions
    else:
        requested_python_versions = sorted(tuple(map(int, python_version.split('.'))) for python_version in python_versions)
        for python_version in requested_python_versions:
            if python_version not in release_per_version:
                sys.exit(f'{python_version} is not in the supported versions')
    python_versions = requested_python_versions

    if not platforms:
        platforms = [sys.platform]
    elif platforms == ['all']:
        platforms = list(PLATFORM_CODES)

    if not addons_path:
        sys.exit('--addons-path is required')

    python_version_strs = {python_version: '.'.join(map(str, python_version)) for python_version in python_versions}

    module_patterns = [p for token in (modules or []) for p in token.split(',')]
    all_modules_requirements = get_all_requirements(addons_path, module_patterns)

    if mode == 'json':
        return json.dumps(all_modules_requirements, indent=2) + '\n'

    if mode == 'debian':
        requirements_by_apt = {}
        for requirement_spec in all_modules_requirements:
            apt = requirement_spec.get('apt')
            if not apt or not _is_wanted(requirement_spec, include_test, include_optional):
                continue
            requirements_by_apt.setdefault(requirement_spec.get('pypi') or apt, requirement_spec)

        lines = []
        for key, requirement_spec in sorted(requirements_by_apt.items(), key=lambda entry: entry[0].casefold()):
            name = requirement_spec.get('pypi') or key
            applies_on_linux = False
            for specifier_suffix in requirement_spec.get('requirement_specifiers') or ['']:
                marker = Requirement(name + specifier_suffix).marker
                if any(marker is None or marker.evaluate({'python_version': python_version_strs[python_version], 'sys_platform': 'linux'}) for python_version in python_versions):
                    applies_on_linux = True
                    break
            if applies_on_linux:
                lines.append(f' {requirement_spec["apt"]},\n')
        return ''.join(lines)
    # mode == requirement
    requirements_by_pypi = {}
    for requirement_spec in all_modules_requirements:
        pypi = requirement_spec.get('pypi')
        if not pypi or not _is_wanted(requirement_spec, include_test, include_optional) or (without_apt and requirement_spec.get('apt')):
            continue
        requirements_by_pypi.setdefault(pypi, requirement_spec)

    if precomputed_versions is None:
        precomputed_versions = {}
        if VERSIONS_FILE.is_file():
            with VERSIONS_FILE.open(encoding='utf8') as f:
                precomputed_versions = json.load(f)

        # the cache file may be stale/incomplete (different addons-path, a newly
        # declared requirement, ...): top up whatever it never actually checked
        apt_names = sorted({_apt_name(r) for r in requirements_by_pypi.values() if _apt_name(r)})
        missing_names = sorted({
            name for python_version in python_versions
            for name in apt_names
            if name not in precomputed_versions.get(python_version_strs[python_version], {})
        })
        if missing_names:
            needed_release_per_version = {pv: release_per_version[pv] for pv in python_versions}
            for pv_str, versions_by_name in fetch_all_versions(missing_names, needed_release_per_version).items():
                precomputed_versions.setdefault(pv_str, {}).update(versions_by_name)
    lines = []
    security_used = False
    for pypi, requirement_spec in sorted(requirements_by_pypi.items(), key=lambda entry: entry[0].casefold()):
        for specifier_suffix in requirement_spec.get('requirement_specifiers') or ['']:
            requirement = Requirement(pypi + specifier_suffix)
            marker = requirement.marker

            applicable_python_versions = [
                python_version for python_version in python_versions
                if marker is None or any(marker.evaluate({'python_version': python_version_strs[python_version], 'sys_platform': p}) for p in platforms)
            ]
            if not applicable_python_versions:
                continue  # doesn't apply to any requested python version/platform combination

            linux_python_versions = [
                python_version for python_version in applicable_python_versions
                if marker is None or marker.evaluate({'python_version': python_version_strs[python_version], 'sys_platform': 'linux'})
            ]

            if not linux_python_versions:
                pin = str(requirement.specifier) if requirement.specifier else ''
                marker_text = str(marker).replace('"', "'") if marker else ''
                lines.append(f'{pypi}{pin} ; {marker_text}\n' if marker_text else f'{pypi}{pin}\n')
                continue

            security_entries = [] if ignore_security else requirement_spec.get('security') or []

            per_python_version_constraint = {}
            per_python_version_comment = {}
            for python_version in linux_python_versions:
                if requirement.specifier:
                    per_python_version_constraint[python_version] = str(requirement.specifier)
                    continue

                apt_name = _apt_name(requirement_spec)
                raw_version = precomputed_versions.get(python_version_strs[python_version], {}).get(apt_name) if apt_name else None
                version = parse_version(raw_version) if raw_version else None
                for security_entry in security_entries:
                    spec_text, _, comment = security_entry.partition('#')
                    sec_requirement = Requirement(pypi + spec_text.strip())
                    if sec_requirement.marker is not None and not sec_requirement.marker.evaluate({'python_version': python_version_strs[python_version], 'sys_platform': 'linux'}):
                        continue
                    sec_spec = next(iter(sec_requirement.specifier))
                    sec_version = parse_version(sec_spec.version)
                    if sec_version and (sec_spec.operator == '==' or not version or sec_version > version):
                        version, per_python_version_comment[python_version] = sec_version, comment.strip()
                        security_used = True
                    break
                per_python_version_constraint[python_version] = f'=={".".join(map(str, version))}' if version else ''

            groups = {}
            for python_version, constraint in per_python_version_constraint.items():
                groups.setdefault(constraint, []).append(python_version)

            for constraint, matching_python_versions in groups.items():
                matching_python_versions = set(matching_python_versions)
                python_version_markers = [None]
                if matching_python_versions != set(python_versions):
                    python_version_markers = []
                    i = 0
                    while i < len(python_versions):
                        if python_versions[i] not in matching_python_versions:
                            i += 1
                            continue
                        start = i
                        while i < len(python_versions) and python_versions[i] in matching_python_versions:
                            i += 1
                        python_version_marker = f"python_version >= '{python_version_strs[python_versions[start]]}'"
                        if i < len(python_versions):
                            python_version_marker += f" and python_version < '{python_version_strs[python_versions[i]]}'"
                        python_version_markers.append(python_version_marker)

                comment = next((per_python_version_comment[python_version] for python_version in matching_python_versions if python_version in per_python_version_comment), '')
                for python_version_marker in python_version_markers:
                    marker_parts = []
                    if marker is not None and 'sys_platform' in specifier_suffix:
                        marker_parts.append(str(marker).replace('"', "'"))
                    if python_version_marker:
                        marker_parts.append(python_version_marker)
                    line = f'{pypi}{constraint}'
                    if marker_parts:
                        line += ' ; ' + ' and '.join(marker_parts)
                    if comment:
                        line += f'  # {comment}'
                    lines.append(line + '\n')

    if ignore_security:
        security_note = 'security pins ignored'
    else:
        security_note = 'security pins applied' if security_used else 'no security pins needed'
    py_version_str = ', '.join(python_version_strs[python_version] for python_version in python_versions)
    platforms_str = ', '.join(platforms)
    header = f'# Automatically generated for python versions {py_version_str} on {platforms_str} platform ({security_note})\nRequirements version are mostly based on their debian package and using the pypi packages is not adviced for production\n'
    return header + ''.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--mode', choices=['requirement', 'debian', 'json'], default='requirement',
        help='requirement: requirements.txt; debian: apt Depends lines for linux; json: raw collected requirements',
    )
    parser.add_argument(
        '-py', '--python-versions', nargs='+',
        help="Python versions to support in the requirement. Use the current version is not defined, check release.py if all",
    )
    parser.add_argument(
        '-pl', '--platforms', nargs='+',
        help=f"Platforms to support ({', '.join(PLATFORM_CODES)}, or 'all'). Uses the current platform if not defined",
    )
    parser.add_argument(
        '--addons-path', nargs='+',
        help="List of addons path to check for addons",
    )
    parser.add_argument(
        '-o', '--output', help="output path",
    )
    parser.add_argument(
        '-m', '--modules', nargs='+',
        help="fnmatch patterns of Odoo modules to keep, comma or space separated, "
             "a leading '-' excludes (e.g. '*' '-l10n*'). Kept modules' own dependencies "
             "are always included. Defaults to every module found",
    )
    parser.add_argument(
        '--ignore-security', action="store_true",
        help="Ignore the 'security' minimum version overrides declared in manifests",
    )
    parser.add_argument(
        '-io', '--include_optional', action="store_true",
        help="Include optional dependencies",
    )
    parser.add_argument(
        '-it', '--include_test', action="store_true",
        help="Include test dependencies",
    )
    parser.add_argument(
        '--without-apt', action="store_true",
        help="Only list requirements without an apt equivalent",
    )

    args = parser.parse_args()
    output = generate_requirements(
        addons_path=args.addons_path,
        mode=args.mode,
        python_versions=args.python_versions,
        platforms=args.platforms,
        modules=args.modules,
        ignore_security=args.ignore_security,
        without_apt=args.without_apt,
        include_test=args.include_test,
        include_optional=args.include_optional,
    )
    if args.output:
        with open(args.output, 'w', encoding='utf8') as f:
            f.write(output)
    else:
        sys.stdout.write(output)
