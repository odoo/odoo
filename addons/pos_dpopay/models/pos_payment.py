# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    dpopay_rrn = fields.Char(string='RRN', help="Retrieval Reference Number generated for the DPO Pay transaction.")
    dpopay_transaction_ref = fields.Char(string='Transaction Reference', help="Reference number required for Mobile Money refund transactions.")
    dpopay_mobile_money_phone = fields.Char(string='Mobile Money Phone Number(Last 4 Digit)', help="Customer's phone number used to complete the Mobile Money payment.")
