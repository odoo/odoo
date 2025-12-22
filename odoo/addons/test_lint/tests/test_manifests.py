# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from ast import literal_eval
from os.path import join as opj

from odoo.modules import get_modules
from odoo.modules.module import _DEFAULT_MANIFEST, module_manifest, get_module_path
from odoo.tests import BaseCase
from odoo.tools.misc import file_open, file_path

_logger = logging.getLogger(__name__)

MANIFEST_KEYS = {
    'name', 'icon', 'addons_path', 'license',  # mandatory keys
    *_DEFAULT_MANIFEST,                        # optional keys
    'contributors', 'maintainer', 'url',       # unused "informative" keys
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
