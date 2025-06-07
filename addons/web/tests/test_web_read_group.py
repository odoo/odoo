from odoo import fields
from odoo.tests import common


@common.tagged('post_install', '-at_install')
class TestWebReadGroup(common.TransactionCase):

    def test_web_read_group_with_date_groupby_and_limit(self):
        res_partner_model_id = self.env["ir.model"].search([("model", "=", "res.partner")]).id
        self.env["ir.model.fields"].create({
            "name": "x_date",
            "ttype": "date",
            "model": "res.partner",
            "model_id": res_partner_model_id,
        })
        first, second = self.env["res.partner"].create([
            {
                "name": "first",
                "x_date": fields.Date.to_date("2021-06-01")
            },
            {
                "name": "second",
                "x_date": fields.Date.to_date("2021-07-01")
            }
        ])
        groups = self.env["res.partner"].web_read_group([["id", "in", [first.id, second.id]]], [], groupby=["x_date"], limit=1)
        self.assertEqual(groups["length"], 2)
