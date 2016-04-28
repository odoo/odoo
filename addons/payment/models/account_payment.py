# coding: utf-8

from odoo import fields, models

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_transaction_id = fields.Many2one('payment.transaction', string="Payment Transaction")
