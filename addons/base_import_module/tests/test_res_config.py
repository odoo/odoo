# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

import odoo.tests
from odoo.exceptions import UserError


def manifest_content(manifest={}, /, **values):
    return json.dumps({
        'author': 'Odoo S.A.',
        'license': 'LGPL-3',
        **manifest,
        **values,
    }).encode()


def archive(files):
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zipf:
        for path, data in files:
            zipf.writestr(path, data)
    return buffer


@odoo.tests.tagged('post_install', '-at_install')
class TestResConfigAppstoreModules(odoo.tests.TransactionCase):
    """Test the `x_module_<name>` mechanism on `res.config.settings`: like
    `module_<name>` fields, checking one and saving should install the
    corresponding module, except it is fetched from the Odoo Apps store.
    The actual installs are faked as to not get errors during testing
    """

    def _add_x_module_field(self, name, ttype='boolean'):
        self.env['ir.model.fields'].create({
            'model_id': self.env['ir.model']._get_id('res.config.settings'),
            'name': name,
            'field_description': name,
            'ttype': ttype,
        })

    def test_field_must_be_boolean(self):
        self._add_x_module_field('x_module_not_boolean', ttype='char')
        with self.assertRaises(Exception):
            self.env['res.config.settings']._get_appstore_fields()

    def test_unchecked_field_does_not_install(self):
        self._add_x_module_field('x_module_industry_foo')
        settings = self.env['res.config.settings'].create({'x_module_industry_foo': False})
        # fake out the real install so we can check whether it got called at all
        with patch.object(type(self.env['ir.module.module']), '_install_data_module') as install:
            settings.execute()
        install.assert_not_called()

    def test_checked_field_installs_from_appstore(self):
        self._add_x_module_field('x_module_industry_foo')
        settings = self.env['res.config.settings'].create({'x_module_industry_foo': True})
        # fake out the real install so we can assert it was called with the right module name
        with patch.object(type(self.env['ir.module.module']), '_install_data_module') as install:
            settings.execute()
        install.assert_called_once_with('industry_foo')

    def test_checked_field_already_installed_does_not_reinstall(self):
        # 'base' is always installed, so `module.state == 'installed'` and the
        # appstore download/install must be skipped entirely.
        self._add_x_module_field('x_module_base')
        settings = self.env['res.config.settings'].create({'x_module_base': True})
        # fake out the real install so we can check it was skipped, as expected
        with patch.object(type(self.env['ir.module.module']), '_install_data_module') as install:
            settings.execute()
        install.assert_not_called()

    def test_checked_field_installs_real_module_end_to_end(self):
        """Test the full chain (res.config.settings -> _install_data_module ->
        _prepare_data_module_import -> base.import.module -> _import_zipfile),
        mocking only the network download. Also pins the version to a final
        release, since the pre-release guard (tested separately below)
        would otherwise block the install on the master branch, and skips the
        "is this a real Odoo industry" check (tested separately below too),
        since "industry_bar" is a made-up name that wouldn't actually be found."""
        self._add_x_module_field('x_module_industry_bar')
        zip_data = archive([
            ('industry_bar/__manifest__.py', manifest_content()),
        ]).getvalue()
        settings = self.env['res.config.settings'].create({'x_module_industry_bar': True})
        # pin the version to a release, since the pre-release guard would otherwise block this;
        # skip the appstore-identity check, since "industry_bar" isn't a real published module;
        # fake out only the network download (the actual boundary to apps.odoo.com), let
        # everything downstream of it (dependency check, wizard, _import_zipfile) run for real
        with patch('odoo.addons.base_import_module.models.ir_module.version_info', (19, 0, 0, 'final', 0, '')), \
             patch.object(type(self.env['ir.module.module']), '_check_is_odoo_industry'), \
             patch.object(type(self.env['ir.module.module']), '_download_data_module_zip', return_value=zip_data):
            settings.execute()
        module = self.env['ir.module.module'].search([('name', '=', 'industry_bar')])
        self.assertEqual(module.state, 'installed')
        self.assertEqual(module.module_type, 'industries')

    def test_check_is_odoo_industry_rejects_unknown_module(self):
        """Nothing found on the store at all (e.g. a regular, non-industry
        module, or a typo) must be rejected before ever attempting a download."""
        with patch.object(type(self.env['ir.module.module']), '_get_modules_from_apps', return_value=[]):
            with self.assertRaises(UserError):
                self.env['ir.module.module']._check_is_odoo_industry('not_a_real_industry')

    def test_check_is_odoo_industry_rejects_non_odoo_author(self):
        """Found on the store, approved, but not authored by Odoo must be rejected."""
        with patch.object(type(self.env['ir.module.module']), '_get_modules_from_apps',
                           return_value=[{'author': 'Some Community Dev', 'approved': True}]):
            with self.assertRaises(UserError):
                self.env['ir.module.module']._check_is_odoo_industry('third_party_industry')

    def test_check_is_odoo_industry_rejects_not_approved(self):
        """Found on the store, authored by Odoo, but not (yet) approved must be rejected."""
        with patch.object(type(self.env['ir.module.module']), '_get_modules_from_apps',
                           return_value=[{'author': 'Odoo S.A.', 'approved': False}]):
            with self.assertRaises(UserError):
                self.env['ir.module.module']._check_is_odoo_industry('unapproved_industry')

    def test_check_is_odoo_industry_accepts_real_industry(self):
        """Found on the store, approved and authored by Odoo: no error."""
        with patch.object(type(self.env['ir.module.module']), '_get_modules_from_apps',
                           return_value=[{'author': 'Odoo S.A.', 'approved': True}]):
            self.env['ir.module.module']._check_is_odoo_industry('construction')

    def test_pre_release_version_blocks_install(self):
        """The appstore has nothing published for pre-release versions, so
        installs must fail with a clear error instead of a confusing network
        failure (404/connection error)."""
        self._add_x_module_field('x_module_industry_baz')
        settings = self.env['res.config.settings'].create({'x_module_industry_baz': True})
        # pretend we're running a pre-release version, to trigger the guard without
        # needing to actually be on one
        with patch('odoo.addons.base_import_module.models.ir_module.version_info', (19, 0, 0, 'alpha', 1, '')):
            with self.assertRaises(UserError):
                settings.execute()
