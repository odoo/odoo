from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Default Currency",
        readonly=True,
    )
