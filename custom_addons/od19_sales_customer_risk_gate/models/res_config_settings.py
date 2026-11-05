from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_credit_hold_enabled = fields.Boolean(
        related="company_id.od19_credit_hold_enabled",
        readonly=False,
        string="Credit Aging Hold",
    )
    od19_credit_hold_max_overdue_days = fields.Integer(
        related="company_id.od19_credit_hold_max_overdue_days",
        readonly=False,
        string="Max Overdue Days",
    )
    od19_credit_hold_max_overdue_amount = fields.Monetary(
        related="company_id.od19_credit_hold_max_overdue_amount",
        readonly=False,
        string="Max Overdue Amount",
        currency_field="currency_id",
    )
