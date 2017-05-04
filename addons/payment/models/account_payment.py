# coding: utf-8

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_transaction_id = fields.Many2one('payment.transaction', string="Payment Transaction")
    payment_token_id = fields.Many2one('payment.token', string="Saved payment token", domain=[('acquirer_id.auto_confirm', '!=', 'authorize')],
                                       help="Note that tokens from acquirers set to only authorize transactions (instead of capturing the amount) are not available.")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = {}
        if self.partner_id:
            partners = self.partner_id | self.partner_id.commercial_partner_id | self.partner_id.commercial_partner_id.child_ids
            res['domain'] = {'payment_token_id': [('partner_id', 'in', partners.ids), ('acquirer_id.auto_confirm', '!=', 'authorize')]}

        return res

    @api.onchange('payment_method_id', 'journal_id')
    def _onchange_payment_method(self):
        if self.payment_method_code == 'electronic':
            self.payment_token_id = self.env['payment.token'].search([('partner_id', '=', self.partner_id.id), ('acquirer_id.auto_confirm', '!=', 'authorize')], limit=1)
        else:
            self.payment_token_id = False

    @api.model
    def create(self, vals):
        account_payment = super(AccountPayment, self).create(vals)

        if account_payment.payment_token_id:
            account_payment._do_payment()
        return account_payment

    def _do_payment(self):
        if self.payment_token_id.acquirer_id.auto_confirm == 'authorize':
            raise ValidationError('This feature is not available for payment acquirers set to the "Authorize" mode.\n'
                                  'Please use a token from another provider than %s.' % self.payment_token_id.acquirer_id.name)
        reference = "P-%s-%s" % (self.id, datetime.datetime.now().strftime('%y%m%d_%H%M%S'))
        tx = self.env['payment.transaction'].create({
            'amount': self.amount,
            'acquirer_id': self.payment_token_id.acquirer_id.id,
            'type': 'server2server',
            'currency_id': self.currency_id.id,
            'reference': reference,
            'payment_token_id': self.payment_token_id.id,
            'partner_id': self.partner_id.id,
            'partner_country_id': self.partner_id.country_id.id,
        })

        s2s_result = tx.s2s_do_transaction()

        if not s2s_result or tx.state != 'done':
            raise ValidationError(_("Payment transaction failed (%s)") % tx.state_message)

        self.payment_transaction_id = tx
