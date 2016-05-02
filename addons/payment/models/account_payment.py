# coding: utf-8

import datetime
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = {}
        if self.partner_id:
            res['domain'] = {'electronic_payment_method_id': [('partner_id', '=', self.partner_id.id)]}

        return res

    payment_transaction_id = fields.Many2one('payment.transaction', string="Payment Transaction")
    electronic_payment_method_id = fields.Many2one('payment.method', string="Saved payment method")

    def _do_payment(self):
        tx_obj = self.env['payment.transaction']
        reference = "PAYMENT-%s-%s" % (self.id, datetime.datetime.now().strftime('%y%m%d_%H%M%S'))

        tx_values = {
            'amount': self.amount,
            'acquirer_id': self.electronic_payment_method_id.acquirer_id.id,
            'type': 'server2server',
            'currency_id': self.currency_id.id,
            'reference': reference,
            'payment_method_id': self.electronic_payment_method_id.id,
            'partner_id': self.partner_id.id,
            'partner_country_id': self.partner_id.country_id.id,
        }

        tx = tx_obj.create(tx_values)

        s2s_result = tx.s2s_do_transaction()

        if not s2s_result or tx.state != 'done': # todo jov: what about pending transactions
            raise ValidationError(_("Payment transaction failed (%s)") % tx.state_message)

        self.payment_transaction_id = tx

    @api.model
    def create(self, vals):
        res = super(AccountPayment, self).create(vals)

        if res.electronic_payment_method_id:
            res._do_payment()

        return res

