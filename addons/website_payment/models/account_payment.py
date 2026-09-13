from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_donation = fields.Boolean(
        related="transaction_id.is_donation",
        string="Is Donation",
    )
