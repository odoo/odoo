from odoo import fields, models


class EventEvent(models.Model):
    _inherit = "event.event"

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )
