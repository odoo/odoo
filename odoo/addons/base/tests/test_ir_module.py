from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged, TransactionCase
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestModuleCountryFixtures(TransactionCase):
    @mute_logger('odoo.modules.module')
    def test_fixture_companies_do_not_auto_install_localizations(self):
        fixture_ids = self.env['ir.model.data'].search([
            ('module', '=', 'base'), ('model', '=', 'res.company'), ('name', '=like', 'test_company%'),
        ]).mapped('res_id')
        real_countries = self.env['res.company'].search([('id', 'not in', fixture_ids)]).country_id
        country = (self.env['res.company'].browse(fixture_ids).country_id - real_countries)[:1]
        self.assertTrue(country)
        Modules = self.env['ir.module.module']
        dependency = Modules.create({'name': 'test_fixture_install_dependency', 'state': 'uninstalled'})
        localization = Modules.create({
            'name': 'test_fixture_install_localization',
            'state': 'uninstalled',
            'auto_install': True,
            'country_ids': [Command.link(country.id)],
            'dependencies_id': [Command.create({
                'name': dependency.name, 'auto_install_required': True,
            })],
        })
        dependency.button_install()
        self.assertEqual(localization.state, 'uninstalled')

        dependency.state = 'uninstalled'
        self.env['res.company'].create({'name': 'Real Localization Company', 'country_id': country.id})
        dependency.button_install()
        self.assertEqual(localization.state, 'to install')


@tagged('at_install', '-post_install')  # LEGACY at_install
class IrModuleCase(TransactionCase):
    @mute_logger("odoo.modules.module")
    def test_missing_module_icon(self):
        module = self.env["ir.module.module"].create({"name": "missing"})
        base = self.env["ir.module.module"].search([("name", "=", "base")])
        self.assertEqual(base.icon_image.content, module.icon_image.content)

    @mute_logger("odoo.modules.module")
    def test_new_module_icon(self):
        module = self.env["ir.module.module"].new({"name": "missing"})
        self.assertFalse(module.icon_image)

    @mute_logger("odoo.modules.module")
    def test_module_wrong_icon(self):
        module = self.env["ir.module.module"].create(
            {"name": "wrong_icon", "icon": "/not/valid.png"}
        )
        self.assertFalse(module.icon_image)

    @mute_logger("odoo.modules.module")
    def test_falsy_res_id(self):
        module = self.env["ir.module.module"].create(
            {"name": "get_views_test", "state": "installed"},
        )
        report = self.env['ir.actions.report'].create({
            'name': 'good_data_report',
            'report_name': 'web_studio.test_duplicate_foo',
            'model': 'res.users',
        })
        self.env["ir.model.data"].create({
            "module": "get_views_test",
            "name": "bad_data",
            "model": "ir.actions.report",
            "res_id": 0,
        })
        self.env["ir.model.data"].create({
            "module": "get_views_test",
            "name": "good_data",
            "model": "ir.actions.report",
            "res_id": report.id,
        })
        self.assertEqual(module.reports_by_module, "good_data_report")
        self.assertEqual(module.state, "installed")
        module.module_uninstall()
        self.assertEqual(module.state, "uninstalled")


@tagged('at_install', '-post_install')
class TestModuleCategory(TransactionCase):

    def test_parent_circular_dependencies(self):
        Cats = self.env['ir.module.category']

        def create(name, **kw):
            return Cats.create(dict(kw, name=name))

        category_a = create('A', parent_id=False)
        category_b = create('B', parent_id=category_a.id)
        category_c = create('C', parent_id=category_b.id)

        with self.assertRaises(ValidationError):
            category_a.write({'parent_id': category_c.id})
        with self.assertRaises(ValidationError):
            category_b.write({'parent_id': category_b.id})
