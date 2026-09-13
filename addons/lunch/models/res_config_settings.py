from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
    )
    company_lunch_minimum_threshold = fields.Float(
        related="company_id.lunch_minimum_threshold",
        string="Maximum Allowed Overdraft",
        readonly=False,
    )
    company_lunch_notify_message = fields.Html(
        related="company_id.lunch_notify_message",
        string="Lunch notification message",
        readonly=False,
    )
