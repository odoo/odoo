import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from odoo.modules import Manifest, get_manifest
from odoo.modules.module import Requirement
from odoo.tests.common import BaseCase, _preexec, no_retry

import odoo.addons

_logger = logging.getLogger(__name__)


@no_retry
class TestModulesDependencies(BaseCase):
    def setUp(self):
        self.odoo_path = Path(__file__).parents[4]

    def test_manifest_dependencies(self):
        with open("/tmp/odoo_dependencies.json", mode="w+", encoding='utf8') if os.environ.get('TEST_MANIFEST_DEPENDENCIES_DEBUG') else tempfile.NamedTemporaryFile() as temp_file:

            if not temp_file.read():
                odoo_ls_params = [
                    'odoo_ls_server',
                    '--list-python-dependencies',
                    '--community-path', self.odoo_path,
                    '-o', temp_file.name,
                ]
                for addon_path in odoo.addons.__path__:
                    odoo_ls_params += ['--tracked-folders', addon_path]

                subprocess.call(odoo_ls_params, preexec_fn=_preexec)

            result = json.load(temp_file)

        cache = {}

        def _get_manifest_dependencies(odoo_addon):
            if odoo_addon not in cache:
                manifest = get_manifest(odoo_addon)
                manifest_dependencies = {}
                for external_dependecy_info in manifest['external_dependencies']:
                    if not isinstance(external_dependecy_info, dict):
                        _logger.warning('External dependency %s of %s is not in the correct format in %s/__manifest__.py', external_dependecy_info, odoo_addon, manifest.path)
                        continue
                    unknown_keys = set(external_dependecy_info.keys()) - {'pypi', 'optional', 'test', 'modules', 'apt', 'core', 'bin', 'custom_install', 'dependencies', 'requirement_specifiers'}
                    if unknown_keys:
                        _logger.warning('Unsuported keys %s in external dependencies of %s', sorted(unknown_keys), odoo_addon)
                    if 'bin' in external_dependecy_info:
                        continue
                    python_modules = external_dependecy_info.get('modules', [external_dependecy_info['pypi']])
                    for python_module in python_modules:
                        if python_module in sys.stdlib_module_names:
                            _logger.error('Dependency %s in manifest of module %s is part of the Python standard library and should not be declared as an external dependency', python_module, odoo_addon)
                        manifest_dependencies[python_module] = external_dependecy_info

                cache[odoo_addon] = manifest_dependencies
            return cache[odoo_addon]

        for odoo_addon, data in result['modules'].items():
            python_deps = {d['name']: d for d in data['dependencies'] if d['type'] == 'python_module' and d['name'] not in sys.stdlib_module_names}
            manifest_dependencies = _get_manifest_dependencies(odoo_addon)
            if manifest_dependencies and not any(python_module in python_deps for python_module in manifest_dependencies):
                for python_module, manifes_dependency in manifest_dependencies.items():
                    if python_module not in python_deps:
                        log = _logger.warning
                        message = ''
                        if manifes_dependency.get('core'):
                            log = _logger.info
                            message = ' (marked as core)'
                            # todo check should be postpone to check if at least one module depends on it in the dependant addon.
                        log('Python module %s is not in the dependency of %s but is declared in the manifest%s', python_module, odoo_addon, message)
            for dep_name, python_dep in python_deps.items():
                manifest_dependency = manifest_dependencies.get(dep_name)
                from_module = ''
                check_flags = True
                if not manifest_dependency:
                    check_flags = False
                    for odoo_addon_depend in data['manifest_depends']:
                        dependency_name = odoo_addon_depend['name']
                        depends_manifest_dependencies = _get_manifest_dependencies(dependency_name)
                        dependent_manifest_dependency = depends_manifest_dependencies.get(dep_name)
                        if (
                            dependent_manifest_dependency and (
                                not manifest_dependency
                                or dependent_manifest_dependency.get('optional', False) < manifest_dependency.get('optional', False)
                                or dependent_manifest_dependency.get('test', False) < manifest_dependency.get('test', False)
                            )
                        ):
                            manifest_dependency = dependent_manifest_dependency
                            from_module = f' (from module {dependency_name}) '
                example_usage = ''
                example_non_test_usage = ''
                example_required_usage = ''
                is_test = True
                is_optional = True
                for occurence in python_dep['occurrences']:
                    o_file = occurence['file']
                    o_line = occurence['line']
                    example_usage = f'{o_file}:{o_line}'
                    if not ('/tests/' in o_file or '/test_' in o_file):
                        is_test = False
                        example_non_test_usage = example_usage
                    if occurence['import_context'] != 'try':
                        is_optional = False
                        example_required_usage = example_usage

                if not manifest_dependency:
                    category = ' (test)' if is_test else ' (optional)' if is_optional else ''
                    _logger.error('Missing dependency for %s in manifest of module %s%s: %s', dep_name, odoo_addon, category, example_usage)
                    continue
                if not is_test and manifest_dependency.get('test'):
                    _logger.error('Dependency %s in manifest of module %s %s is marked for test but is used in %s', dep_name, odoo_addon, from_module, example_non_test_usage)
                if not is_optional and manifest_dependency.get('optional'):
                    _logger.error('Dependency %s in manifest of module %s %s is marked for optional but is used in %s outside a try block', dep_name, odoo_addon, from_module, example_required_usage)
                if check_flags and not manifest_dependency.get('core'):
                    if is_test:
                        if not manifest_dependency.get('test'):
                            _logger.warning('Dependency %s in manifest of module %s is not marked as test but is only used in tests', dep_name, odoo_addon)
                    elif is_optional:
                        if not manifest_dependency.get('optional'):
                            _logger.warning('Dependency %s in manifest of module %s is not marked as optional but is only used in try blocks', dep_name, odoo_addon)

    def test_requirements_dependencies(self):
        # check if the requirements.txt is coherent with the external dependencies
        # - all non optional depenency of the manifest should be in the resuirement
        # - all depenencies of the requirement should be in a manifest, if we have main odoo repositories in addons_path

        all_external_dependencies = {}
        for manifest in Manifest.all_addon_manifests():
            for external_dependency in manifest['external_dependencies']:
                if pypi := external_dependency.get('pypi'):
                    all_external_dependencies.setdefault(pypi, []).append((manifest.name, external_dependency))
                    for indirect_dependency in external_dependency.get('dependencies', []):
                        all_external_dependencies.setdefault(indirect_dependency, []).append((manifest.name, external_dependency))
        requirement = (self.odoo_path / 'requirements.txt').read_text()
        requirement_dependencies = {}
        for line in requirement.split('\n'):
            line = line.split('#')[0]
            if not line:
                continue
            req = Requirement(line)
            requirement_dependencies[req.name] = req
            if req.name not in all_external_dependencies:
                _logger.error("Requirement %s is in requirements.txt but is not defined in any manifest", req.name)
            else:
                is_test = True
                is_optional = True
                for _, external_dependency in all_external_dependencies[req.name]:
                    is_test = is_test and external_dependency.get('test')
                    is_optional = is_optional and external_dependency.get('optional')
                if is_test:
                    _logger.info("Requirement %s is in requirements.txt but is only used in tests", req.name)
                elif is_optional:
                    _logger.info("Requirement %s is in requirements.txt but is optional", req.name)

        for package_name, external_dependencies in all_external_dependencies.items():
            if package_name not in requirement_dependencies:
                for module_name, external_dependency in external_dependencies:
                    if not external_dependency.get('optional') and not external_dependency.get('test'):
                        _logger.runbot('Package %s is required in module %s but is not in the requirements.txt', package_name, module_name)
