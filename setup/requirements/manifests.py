import ast
import fnmatch
from pathlib import Path


def get_all_manifests(addons_path):
    manifests = {}
    for path in addons_path:
        for module in Path(path).iterdir():
            manifest_path = module / '__manifest__.py'
            if manifest_path.is_file():
                with manifest_path.open() as f:
                    manifest = ast.literal_eval(f.read())
                    if manifest.get('installable', True):
                        manifests[module.name] = manifest
    return manifests


def select_modules(manifests, patterns):
    if not patterns:
        matching = set(manifests)
    else:
        matching = set()
        for pattern in patterns:
            exclude = pattern.startswith('-')
            matches = {name for name in manifests if fnmatch.fnmatchcase(name, pattern[1:] if exclude else pattern)}
            if exclude:
                matching -= matches
            else:
                matching |= matches

    to_check = list(matching)
    selection = set()
    while to_check:
        name = to_check.pop()
        if name in selection:
            continue
        selection.add(name)
        to_check.extend(manifests.get(name, {}).get('depends', ['base']))
    return selection


def get_all_requirements(addons_path, module_patterns=None):
    manifests = get_all_manifests(addons_path)
    all_requirements = []
    for name in select_modules(manifests, module_patterns):
        manifest = manifests.get(name)
        if not manifest:
            continue
        for external_dependencies in manifest.get('external_dependencies', []):
            external_dependencies['module'] = name
            all_requirements.append(external_dependencies)

    known_pypi = {req['pypi'] for req in all_requirements if req.get('pypi')}
    for requirement_spec in list(all_requirements):
        for indirect in requirement_spec.get('dependencies', []):
            if indirect not in known_pypi:
                known_pypi.add(indirect)
                all_requirements.append({
                    'pypi': indirect,
                    'optional': requirement_spec.get('optional'),
                    'test': requirement_spec.get('test'),
                    'requirement_specifiers': requirement_spec.get('requirement_specifiers'),
                })
    return all_requirements
