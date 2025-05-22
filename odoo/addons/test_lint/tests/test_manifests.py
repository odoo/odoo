# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from ast import literal_eval
from os.path import join as opj
from pathlib import Path

from odoo.modules import get_modules
from odoo.modules.module import _DEFAULT_MANIFEST, module_manifest, get_module_path
from odoo.tests import BaseCase
from odoo.tools.misc import file_open, file_path

DFTL_MANIFEST_DATA_KEYS = ["data", "demo"] + [k for k in _DEFAULT_MANIFEST if k.endswith("_xml")]
MANIFEST_DATA_DIRS = ["data", "datas", "demo", "demos", "report", "reports", "security", "template", "templates", "view", "views", "wizard", "wizards"]
MANIFEST_DATA_EXTS = [".csv", ".xml"]
MANIFEST_DATA_NOT_USED_EXCLUDE_KEY = "not_used_exclude"

_logger = logging.getLogger(__name__)

MANIFEST_KEYS = {
    # mandatory keys
    'name', 'icon', 'addons_path', 'author', 'license',
    # optional keys
    *_DEFAULT_MANIFEST,
    # unused "informative" keys
    'contributors', 'maintainer', 'url',
    # to silent data file not used check
    MANIFEST_DATA_NOT_USED_EXCLUDE_KEY,
}


class ManifestLinter(BaseCase):

    def _load_manifest(self, module):
        """Do not rely on odoo/modules/module -> load_manifest
        as we want to check manifests content, independently of the
        values from _DEFAULT_MANIFEST added automatically by load_manifest
        """
        mod_path = get_module_path(module, downloaded=True)
        manifest_file = module_manifest(mod_path)

        manifest_data = {}
        with file_open(manifest_file, mode='r') as f:
            manifest_data.update(literal_eval(f.read()))

        return manifest_data

    def test_manifests(self):
        for module in get_modules():
            with self.subTest(module=module):
                manifest_data = self._load_manifest(module)
                self._test_manifest_keys(module, manifest_data)
                self._test_manifest_values(module, manifest_data)
                self._test_data_files(module, manifest_data)

    def _test_manifest_keys(self, module, manifest_data):
        manifest_keys = manifest_data.keys()
        unknown_keys = manifest_keys - MANIFEST_KEYS
        self.assertEqual(unknown_keys, set(), f"Unknown manifest keys in module {module!r}. Either there are typos or they must be white listed.")

    def _test_manifest_values(self, module, manifest_data):
        verified_keys = [
            'application', 'auto_install',
            'summary', 'description', 'author',
            'demo', 'data', 'test',
            # todo installable ?
        ]

        if len(manifest_data.get('countries', [])) == 1 and 'l10n' not in module:
            _logger.warning(
                "Module %r specific to one single country %r should contain `l10n` in their name.",
                module, manifest_data['countries'][0])

        for key in manifest_data:
            value = manifest_data[key]
            if key in _DEFAULT_MANIFEST:
                if key in verified_keys:
                    self.assertNotEqual(
                       value,
                        _DEFAULT_MANIFEST[key],
                        f"Setting manifest key {key} to the default manifest value for module {module!r}. "
                        "You can remove this key from the dict to reduce noise/inconsistencies between manifests specifications"
                        " and ease understanding of manifest content."
                    )

                expected_type = type(_DEFAULT_MANIFEST[key])
                if not isinstance(value, expected_type):
                    if key != 'auto_install':
                        _logger.warning(
                            "Wrong type for manifest value %s in module %s, expected %s",
                            key, module, expected_type)
                    elif not isinstance(value, list):
                        _logger.warning(
                            "Wrong type for manifest value %s in module %s, expected bool or list",
                            key, module)
                else:
                    if key == 'countries':
                        self._test_manifest_countries_value(module, value)
            elif key == 'icon':
                self._test_manifest_icon_value(module, value)

    def _test_manifest_icon_value(self, module, value):
        self.assertTrue(
            isinstance(value, str),
            f"Wrong type for manifest value icon in module {module!r}, expected string",
        )
        self.assertNotEqual(
            value,
            f"/{module}/static/description/icon.png",
            f"Setting manifest key icon to the default manifest value for module {module!r}. "
            "You can remove this key from the dict to reduce noise/inconsistencies between manifests specifications"
            " and ease understanding of manifest content."
        )
        if not value:
            _logger.warning(
                "Empty value specified as icon in manifest of module %r."
                " Please specify a correct value or remove this key from the manifest.",
                module)
        else:
            path_parts = value.split('/')
            try:
                file_path(opj(*path_parts[1:]))
            except FileNotFoundError:
                _logger.warning(
                    "Icon value specified in manifest of module %s wasn't found in given path."
                    " Please specify a correct value or remove this key from the manifest.",
                    module)

    def _test_manifest_countries_value(self, module, values):
        for value in values:
            if value and len(value) != 2:
                _logger.warning(
                    "Country value %s specified for the icon in manifest of module %s doesn't look like a country code"
                    "Please specify a correct value or remove this key from the manifest.",
                    value, module)

    @staticmethod
    def _get_data_filenames_from_manifest(manifest_data):
        """Get data file names from the manifest keys"""
        for data_key in DFTL_MANIFEST_DATA_KEYS:
            for file_name in manifest_data.get(data_key) or []:
                if Path(file_name).suffix.lower() not in MANIFEST_DATA_EXTS:
                    continue
                yield file_name

    @staticmethod
    def _get_data_filenames_from_module(module):
        """Get data file names from the module path"""
        module_root_path_obj = Path(file_path(module)).resolve()
        for subpath_obj in module_root_path_obj.rglob("*"):
            parts = subpath_obj.relative_to(module_root_path_obj).parts
            if (
                not subpath_obj.is_file()  # is file
                # only depth 2 to comply with guidelines module/data/file.xml
                # not consider different depth module/data/other/file.xml
                or len(parts) != 2
                or parts[0].lower() not in MANIFEST_DATA_DIRS  # only valid dir
                or subpath_obj.suffix.lower() not in MANIFEST_DATA_EXTS  # only valid ext
            ):
                continue
            yield subpath_obj.relative_to(module_root_path_obj).as_posix()

    def _test_data_files(self, module, manifest_data):
        """Check the data xml and csv files referenced from manifest files
        vs the files present in the module data folders
        In order to identify files created in the module but not referenced in the manifest
        Inspired from https://github.com/OCA/odoo-pre-commit-hooks @moylop260 file-not-used check
        """
        manifest_filenames = set(self._get_data_filenames_from_manifest(manifest_data))
        module_filenames = set(self._get_data_filenames_from_module(module))
        # Support exceptions e.g. load from hooks instead of manifest data
        exclude = set(manifest_data.get(MANIFEST_DATA_NOT_USED_EXCLUDE_KEY) or [])
        files_not_used = module_filenames - manifest_filenames - exclude
        mod_path = get_module_path(module, downloaded=True)
        manifest_file = module_manifest(mod_path)
        for file_not_used in files_not_used:
            file_not_used_path = opj(module, file_not_used)
            _logger.warning((
                'File "%s" is not referenced in the manifest. If it is loaded from another source '
                "(e.g. a post_init_hook script), just add it under the section `'%s': ['%s'],` "
                'in %s file to be considered.'),
                file_not_used_path, MANIFEST_DATA_NOT_USED_EXCLUDE_KEY, file_not_used, manifest_file)
        self.assertFalse(bool(files_not_used), f"File(s) not used found in {module}")
