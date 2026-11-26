# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

import odoo.tests

from odoo.addons.base_import_module.models.ir_module import IrModuleModule
from odoo.addons.base_import_module.tests.common import archive, manifest_content


class TestResConfigXIndustry(odoo.tests.TransactionCase):
    """Test the `x_industry_<name>` mechanism on `res.config.settings`: like
    `module_<name>` fields, checking one and saving should install the
    corresponding module, except it is fetched from the Odoo Apps store.
    The actual installs are faked as to not get errors during testing
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        model_id = cls.env['ir.model']._get_id('res.config.settings')
        cls.env['ir.model.fields'].create([
            {'model_id': model_id, 'name': 'x_industry_not_boolean', 'field_description': 'x_industry_not_boolean', 'ttype': 'char'},
            {'model_id': model_id, 'name': 'x_industry_foo', 'field_description': 'x_industry_foo', 'ttype': 'boolean'},
        ])

    def test_non_boolean_field_is_ignored(self):
        names = [name for name, _module_name in self.env['res.config.settings']._get_x_industry_fields()]
        self.assertNotIn('x_industry_not_boolean', names)

    def test_unchecked_field_does_not_install(self):
        settings = self.env['res.config.settings'].create({'x_industry_foo': False})
        # fake out the real install so we can check whether it got called at all
        with patch.object(IrModuleModule, '_install_data_module') as install:
            settings.execute()
        install.assert_not_called()

    def test_checked_field_installs_from_appstore(self):
        settings = self.env['res.config.settings'].create({'x_industry_foo': True})
        # fake out the real install so we can assert it was called with the right module name
        with patch.object(IrModuleModule, '_install_data_module') as install:
            settings.execute()
        install.assert_called_once_with('foo')

    def test_checked_field_already_installed_does_not_reinstall(self):
        # fake an already-installed industry, so `module.state == 'installed'`
        # and the appstore download/install must be skipped entirely.
        self.env['ir.module.module'].create({'name': 'foo', 'state': 'installed'})
        settings = self.env['res.config.settings'].create({'x_industry_foo': True})
        # fake out the real install so we can check it was skipped, as expected
        with patch.object(IrModuleModule, '_install_data_module') as install:
            settings.execute()
        install.assert_not_called()

    def test_unchecked_installed_field_returns_uninstall_wizard(self):
        """Unchecking an installed `x_industry_` field must not uninstall it
        directly: like regular `module_` fields, it must go through the
        `base.module.uninstall` confirmation wizard first."""
        module = self.env['ir.module.module'].create({'name': 'foo', 'state': 'installed'})
        settings = self.env['res.config.settings'].create({'x_industry_foo': False})
        result = settings.execute()
        self.assertEqual(result.get('res_model'), 'base.module.uninstall')
        self.assertEqual(result['context']['default_module_ids'], module.ids)
        self.assertEqual(module.state, 'installed', "the module must not be uninstalled yet, only the wizard shown")

    def test_checked_field_installs_real_module_end_to_end(self):
        """Test the full chain (res.config.settings -> _install_data_module ->
        _prepare_data_module_import -> base.import.module -> _import_zipfile),
        mocking only the network download."""
        zip_data = archive([
            ('foo/__manifest__.py', manifest_content()),
        ]).getvalue()
        settings = self.env['res.config.settings'].create({'x_industry_foo': True})
        # fake out only the network download (the actual boundary to apps.odoo.com), let
        # everything downstream of it (dependency check, wizard, _import_zipfile) run for real
        with patch.object(IrModuleModule, '_download_data_module_zip', return_value=zip_data):
            settings.execute()
        module = self.env['ir.module.module'].search([('name', '=', 'foo')])
        self.assertEqual(module.state, 'installed')
        self.assertTrue(module.is_industry)


class TestResConfigXModule(odoo.tests.TransactionCase):
    """ `x_module_<name>` fields behave like `module_<name>` ones, for fields
    defined in data rather than in Python code. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module = cls.env['ir.module.module'].create({'name': 'test_local_module', 'state': 'uninstalled'})
        cls.env['ir.model.fields'].create({
            'model_id': cls.env['ir.model']._get_id('res.config.settings'),
            'name': 'x_module_test_local_module',
            'field_description': 'x_module_test_local_module',
            'ttype': 'boolean',
        })

    def test_default_reflects_module_state(self):
        self.assertFalse(self.env['res.config.settings'].create({}).x_module_test_local_module)
        self.module.state = 'installed'
        self.assertTrue(self.env['res.config.settings'].create({}).x_module_test_local_module)

    def test_checked_field_installs_module(self):
        settings = self.env['res.config.settings'].create({'x_module_test_local_module': True})
        with patch('odoo.addons.base.models.ir_module.IrModuleModule.button_immediate_install', autospec=True) as install:
            settings.execute()
        install.assert_called_once_with(self.module)

    def test_unchecked_field_returns_uninstall_wizard(self):
        self.module.state = 'installed'
        settings = self.env['res.config.settings'].create({'x_module_test_local_module': False})
        result = settings.execute()
        self.assertEqual(result['res_model'], 'base.module.uninstall')
        self.assertEqual(result['context']['default_module_ids'], self.module.ids)

    def test_unknown_module_is_ignored(self):
        self.env['ir.model.fields'].create({
            'model_id': self.env['ir.model']._get_id('res.config.settings'),
            'name': 'x_module_test_unknown_module',
            'field_description': 'x_module_test_unknown_module',
            'ttype': 'boolean',
        })
        settings = self.env['res.config.settings'].create({'x_module_test_unknown_module': True})
        with patch('odoo.addons.base.models.ir_module.IrModuleModule.button_immediate_install', autospec=True) as install:
            settings.execute()
        install.assert_not_called()

    def test_non_boolean_field_raises(self):
        self.env['ir.model.fields'].create({
            'model_id': self.env['ir.model']._get_id('res.config.settings'),
            'name': 'x_module_test_local_module_char',
            'field_description': 'x_module_test_local_module_char',
            'ttype': 'char',
        })
        with self.assertRaisesRegex(TypeError, "must have type 'boolean'"):
            self.env['res.config.settings'].create({})
