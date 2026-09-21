from odoo import fields, models


class TestReportFormulaEntry(models.Model):
    _name = "test.report.formula.entry"
    _description = "Dated amount a formula report sums"

    name = fields.Char(required=True)
    date = fields.Date(required=True)
    amount = fields.Float()
    partner_id = fields.Many2one(comodel_name="res.partner")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
