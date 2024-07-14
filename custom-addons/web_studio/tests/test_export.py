from lxml import etree
from odoo.tests.common import HttpCase
from odoo.addons.web_studio.controllers import export


class TestExport(HttpCase):
    def test_export_currency_field(self):
        base_currency_field = self.env["res.partner"]._fields.get("currency_id")
        if not base_currency_field or not (base_currency_field.type == "many2one" and base_currency_field.comodel_name == "res.currency"):
            self.env["ir.model.fields"].create({
                "state": "base",
                "name": "x_currency" if base_currency_field else "currency_id",
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "ttype": "many2one",
                "relation": "res.currency"
            })

        IrModelFields = self.env["ir.model.fields"].with_context(studio=True)
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

        studio_module = self.env['ir.module.module'].get_studio_module()
        data = self.env['ir.model.data'].search([
            ('studio', '=', True), ("model", "=", "ir.model.fields"), ("res_id", "in", (currency_field | monetary).ids)
        ])
        content_iter = iter(export.generate_module(studio_module, data))

        file_name = content = None
        while file_name != "data/ir_model_fields.xml":
            file_name, content = next(content_iter)

        arch_fields = etree.fromstring(content)
        records = arch_fields.findall("record")
        currency_field = records[0]
        self.assertEqual(currency_field.find("./field[@name='name']").text, "x_test_currency")
        self.assertEqual(currency_field.find("./field[@name='currency_field']").get("eval"), "False")

        monetary_field = records[1]
        self.assertEqual(monetary_field.find("./field[@name='name']").text, "x_test_monetary")
        self.assertEqual(monetary_field.find("./field[@name='currency_field']").text, "x_test_currency")

        monetary.currency_field = False
        content_iter = iter(export.generate_module(studio_module, data))

        file_name = content = None
        while file_name != "data/ir_model_fields.xml":
            file_name, content = next(content_iter)

        arch_fields = etree.fromstring(content)
        records = arch_fields.findall("record")
        currency_field = records[0]
        self.assertEqual(currency_field.find("./field[@name='name']").text, "x_test_currency")
        self.assertEqual(currency_field.find("./field[@name='currency_field']").get("eval"), "False")

        monetary_field = records[1]
        self.assertEqual(monetary_field.find("./field[@name='name']").text, "x_test_monetary")
        # This assertion is correct technically: the python monetary field will fallback
        # on one of the hardcoded currency field names.
        # For this test though, on res.partner, the actual field will crash
        self.assertEqual(monetary_field.find("./field[@name='currency_field']").get("eval"), "False")
