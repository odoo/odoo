# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    dpo_rrn = fields.Char(
        string='RRN',
        help="Retrieval Reference Number generated for the DPO transaction.",
    )

    dpo_receipt_number = fields.Char(
        string='Receipt Number',
        help="Unique receipt number provided by DPO for this payment.",
    )

    dpo_transaction_ref = fields.Char(
        string='Transaction Reference',
        help="Reference number required for Mobile Money refund transactions.",
    )

    dpo_mobile_money_phone = fields.Char(
        string='Mobile Money Phone Number(Last 4 Digit)',
        help="Customer's phone number used to complete the Mobile Money payment.",
    )
