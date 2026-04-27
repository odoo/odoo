from lxml import etree
from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import BaseCase, HttpCase
from odoo.addons.web_studio.controllers import export
from odoo.addons.web_studio.wizard.studio_export_wizard import _find_circular_dependencies, FIELDS_TO_EXPORT
from odoo.addons.website.tools import MockRequest


class TestExport(HttpCase):
    def test_export_currency_field(self):
        base_currency_field = self.env["res.partner"]._fields.get("currency_id")
        IrModelFields = self.env["ir.model.fields"].with_context(studio=True)
        if not base_currency_field or not (base_currency_field.type == "many2one" and base_currency_field.comodel_name == "res.currency"):
            IrModelFields.create({
                "state": "base",
                "name": "x_currency" if base_currency_field else "currency_id",
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "ttype": "many2one",
                "relation": "res.currency"
            })

        currency_field = IrModelFields.create({
            "name": "x_test_currency",
            "model_id": self.env["ir.model"]._get("res.partner").id,
            "ttype": "many2one",
            "relation": "res.currency"
        })
        monetary = IrModelFields.create({
            "name": "x_test_monetary",
            "model_id": self.env["ir.model"]._get("res.partner").id,
            "ttype": "monetary",
            "currency_field": currency_field.name,
        })

        studio_module = self.env["ir.module.module"].get_studio_module()
        data = self.env['ir.model.data'].search([
            ('studio', '=', True), ("model", "=", "ir.model.fields"), ("res_id", "in", (currency_field | monetary).ids)
        ])
        data = self.env["studio.export.wizard.data"].create(
            [{"model": d.model, "res_id": d.res_id, "studio": d.studio} for d in data]
        )
        wizard = self.env['studio.export.wizard'].create({
            "default_export_data": [Command.set(data.ids)],
            "additional_models": [],
        })
        export_info = wizard._get_export_info()
        content_iter = iter(export.generate_module(studio_module, export_info))

        file_name = content = None
        with MockRequest(self.env):
            while file_name != "data/ir_model_fields.xml":
                file_name, content = next(content_iter)

        arch_fields = etree.fromstring(content)
        records = arch_fields.findall("record")
        currency_field = records[0]
        self.assertEqual(currency_field.find("./field[@name='name']").text, "x_test_currency")
        self.assertEqual(currency_field.find("./field[@name='currency_field']"), None)

        monetary_field = records[1]
        self.assertEqual(monetary_field.find("./field[@name='name']").text, "x_test_monetary")
        self.assertEqual(monetary_field.find("./field[@name='currency_field']").text, "x_test_currency")

        monetary.currency_field = False
        export_info = wizard._get_export_info()
        content_iter = iter(export.generate_module(studio_module, export_info))

        file_name = content = None
        with MockRequest(self.env):
            while file_name != "data/ir_model_fields.xml":
                file_name, content = next(content_iter)

        arch_fields = etree.fromstring(content)
        records = arch_fields.findall("record")
        currency_field = records[0]
        self.assertEqual(currency_field.find("./field[@name='name']").text, "x_test_currency")
        self.assertEqual(currency_field.find("./field[@name='currency_field']"), None)

        monetary_field = records[1]
        self.assertEqual(monetary_field.find("./field[@name='name']").text, "x_test_monetary")
        # This assertion is correct technically: the python monetary field will fallback
        # on one of the hardcoded currency field names.
        # For this test though, on res.partner, the actual field will crash
        self.assertEqual(monetary_field.find("./field[@name='currency_field']"), None)

    def test_export_automation(self):
        ba = self.env["base.automation"].with_context(studio=True).create({
            "name": "Cron BaseAuto",
            "trigger": "on_time",
            "model_id": self.env.ref("base.model_res_users").id,
        })
        data = self.env['ir.model.data'].search([
            ('studio', '=', True), ("model", "=", "base.automation"), ("res_id", "=", ba.id)
        ])

        studio_module = self.env['ir.module.module'].get_studio_module()
        data = self.env["studio.export.wizard.data"].create(
            [{"model": d.model, "res_id": d.res_id, "studio": d.studio} for d in data]
        )
        wizard = self.env['studio.export.wizard'].create({
            "default_export_data": [Command.set(data.ids)],
        })
        export_info = wizard._get_export_info()
        content_iter = iter(export.generate_module(studio_module, export_info))
        file_name = content = None
        with MockRequest(self.env):
            while file_name != "data/base_automation.xml":
                file_name, content = next(content_iter)

        arch = etree.fromstring(content)
        records = arch.findall("record")
        self.assertEqual(len(records), 1)
        record = records[0]
        field_names = {field.get("name") for field in record.findall("./field")}
        self.assertEqual(field_names, {
            "model_id",
            "name",
            "trg_date_range_type",
            "trigger"
        })

    def test_fields_to_export_are_not_excluded(self):
        for model, fields_to_export in FIELDS_TO_EXPORT.items():
            export_model = self.env["studio.export.model"].create({
                "model_id": self.env["ir.model"]._get(model).id,
            })
            excluded_fields = export_model.excluded_fields.mapped("name")
            self.assertEqual(set(fields_to_export), set(fields_to_export) - set(excluded_fields))


@tagged("post_install", "-at_install")
class TestExportTours(HttpCase):
    def test_can_export_new_module(self):
        self.start_tour("/odoo?debug=tests", 'can_export_new_module', login="admin")
        # check the export result made by the tour
        wizard = self.env['studio.export.wizard'].search([], limit=1, order='id desc')
        data, files, circular_dependencies = wizard._get_export_info()
        self.assertEqual(circular_dependencies, [])
        self.assertEqual(data, wizard.default_export_data)
        self.assertEqual(len(wizard.additional_export_data), 0)
        exported_models = {f[0] for f in files}
        self.assertEqual(exported_models, {
            'ir.actions.act_window', 'ir.default',
            'ir.model', 'ir.model.fields', 'ir.model.access',
            'ir.ui.view', 'ir.ui.menu',
        })
        self.assertEqual(len(data.filtered(lambda r: r.model == 'ir.model')), 1)
        self.assertEqual(self.env['ir.model'].browse(data.filtered(lambda r: r.model == 'ir.model').res_id).name, 'My App Records')
        created_menus = self.env['ir.ui.menu'].browse(data.filtered(lambda r: r.model == 'ir.ui.menu').mapped("res_id")).mapped("name")
        self.assertEqual(len(created_menus), 2)
        self.assertTrue('My New App' in created_menus)
        self.assertTrue('My App Records' in created_menus)


class TestCircularDependencies(BaseCase):
    def test_circular_dependencies(self):
        self.assertEqual(_find_circular_dependencies({}), [])
        self.assertEqual(_find_circular_dependencies({1: []}), [])
        self.assertEqual(_find_circular_dependencies({1: [1]}), [])
        self.assertEqual(_find_circular_dependencies({1: [2]}), [])
        self.assertEqual(_find_circular_dependencies({1: [2], 2: [3]}), [])
        self.assertEqual(_find_circular_dependencies({1: [2, 3], 2: [3], 3: [4]}), [])
        self.assertEqual(_find_circular_dependencies({1: [2], 2: [3], 3: [1]}), [[1, 2, 3, 1]])
        self.assertEqual(_find_circular_dependencies({1: [2, 3], 2: [3], 3: [1]}), [[1, 2, 3, 1]])
        self.assertEqual(_find_circular_dependencies({1: [2], 2: [3], 3: [4], 4: [1]}), [[1, 2, 3, 4, 1]])
        self.assertEqual(_find_circular_dependencies({1: [2], 2: [1], 3: [4], 4: [5], 5: [3]}), [[1, 2, 1], [3, 4, 5, 3]])
