from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    od19_revenue_line_id = fields.Many2one(
        "od19.contract.revenue.line",
        string="Revenue Obligation",
        readonly=True,
        copy=False,
        index=True,
        help="Performance obligation this revenue recognition entry belongs to.",
    )
