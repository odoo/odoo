from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_credit_hold_enabled = fields.Boolean(
        string="Credit Aging Hold",
        default=True,
        help="Automatically place a customer on credit hold when their "
        "overdue receivables exceed the tolerance configured below. "
        "The hold blocks new credit sales until the customer is cleared.",
    )
    od19_credit_hold_max_overdue_days = fields.Integer(
        string="Max Overdue Days",
        default=30,
        help="Place the customer on hold when the oldest unpaid invoice is "
        "overdue by more than this number of days. 0 disables the day test.",
    )
    od19_credit_hold_max_overdue_amount = fields.Monetary(
        string="Max Overdue Amount",
        currency_field="currency_id",
        default=0.0,
        help="Place the customer on hold when total overdue receivables "
        "exceed this amount. 0 disables the amount test.",
    )
