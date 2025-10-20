# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from os.path import join as opj

from odoo.modules.module import _DEFAULT_MANIFEST, Manifest
from odoo.tests import BaseCase, HttpCase, tagged
from odoo.tools.misc import file_path

_logger = logging.getLogger(__name__)

MANIFEST_KEYS = {
    # mandatory keys
    'name', 'icon', 'addons_path', 'author', 'license',
    # optional keys
    *_DEFAULT_MANIFEST,
    # unused "informative" keys
    'contributors', 'maintainer', 'url',
}


@tagged('at_install', '-post_install')  # LEGACY at_install
class ManifestLinter(BaseCase):

    def test_manifests(self):
        for manifest in Manifest.all_addon_manifests():
            with self.subTest(module=manifest.name):
                # we want to check the content of the manifest directly without
                # parsed values
                self._test_manifest_keys(manifest)
                self._test_manifest_values(manifest)

    def _test_manifest_keys(self, manifest_data: Manifest):
        manifest_keys = manifest_data._Manifest__manifest_content.keys()
        unknown_keys = manifest_keys - MANIFEST_KEYS
        self.assertEqual(unknown_keys, set(), f"Unknown manifest keys in module {manifest_data.name!r}. Either there are typos or they must be white listed.")

    def _test_manifest_values(self, manifest_data: Manifest):
        module = manifest_data.name
        verified_keys = [
            'application',
            'auto_install',
            'category',
            'data',
            'demo',
            'description',
            'external_dependencies',
            'iap_paid_service',
            'installable',
            'post_init_hook',
            'post_load',
            'pre_init_hook',
            'summary',
            'test',
            'version',
            'website',
        ]

        if len(manifest_data.get('countries', [])) == 1 and 'l10n' not in module:
            _logger.warning(
                "Module %r specific to one single country %r should contain `l10n` in their name.",
                module, manifest_data['countries'][0])

        for key, value in manifest_data._Manifest__manifest_content.items():
            if key in _DEFAULT_MANIFEST:
                if key in verified_keys:
                    self.assertNotEqual(
                       value,
                        _DEFAULT_MANIFEST[key],
                        f"Setting manifest key {key} to the default manifest value for module {module!r}. "
                        "You can remove this key from the dict to reduce noise/inconsistencies"
                        " between manifests specifications and ease understanding of manifest"
                        " content."
                    )
                    if key == 'summary':
                        self.assertNotIn(
                            '\n',
                            value,
                            f"Module {module!r} summary should be a one-line short description",
                        )
                    elif key == 'website':
                        self.assertNotEqual(
                            value,
                            'https://www.odoo.com',
                            f"Module {module!r} website is redirecting to odoo.com, which is"
                            " useless and should be avoid unless there is a dedicated page for it.",
                        )
                        self.assertEqual(
                            bool(value),
                            value.startswith('https://'),
                            f"Module {module!r} website ({value}) should be a valid and secure url",
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
                elif key == 'countries':
                    self._test_manifest_countries_value(module, value)
            elif key == 'icon':
                self._test_manifest_icon_value(module, value)
            elif key == 'license':
                self._test_manifest_license(module, manifest_data, value)

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
                    "Country value %s specified for the icon in manifest of module %s doesn't look like a country code."
                    "Please specify a correct value or remove this key from the manifest.",
                    value, module)

    def _test_manifest_license(self, module: str, manifest: Manifest, value: str):
        if "enterprise" in manifest.addons_path:
            self.assertEqual(
                "OEEL-1",
                value,
                f"Module {module!r} is an enterprise module and should be licensed under the Odoo"
                " Enterprise License (OEEL-1)",
            )
        else:
            self.assertEqual(
                "LGPL-3",
                value,
                f"Module {module!r} is opensource and should be licensed under the LGPL license.",
            )


@tagged('-standard', 'external', 'at_install', '-post_install')
class ManifestNightlyLinter(HttpCase):

    def test_manifests_websites(self):
        checked = set()
        for manifest in Manifest.all_addon_manifests():
            if (
                (url := manifest.get('website', ''))
                and url not in checked
                # Do not request non-odoo pages every night
                and url.startswith('https://www.odoo.com')
            ):
                module = manifest.name
                with self.subTest(module=module):
                    res = self.url_open(url)
                    checked.add(url)
                    self.assertEqual(
                        res.status_code, 200,
                        f"Module {module!r} website link is broken: '{url}'",
                    )
