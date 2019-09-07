# coding: utf-8

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_transaction_id = fields.Many2one('payment.transaction', string='Payment Transaction', readonly=True)
    payment_token_id = fields.Many2one('payment.token', string="Saved payment token", domain=[('acquirer_id.capture_manually', '=', False)],
                                       help="Note that tokens from acquirers set to only authorize transactions (instead of capturing the amount) are not available.")

    def _get_payment_chatter_link(self):
        self.ensure_one()
        return '<a href=# data-oe-model=account.payment data-oe-id=%d>%s</a>' % (self.id, self.name)

    @api.onchange('partner_id', 'payment_method_id', 'journal_id')
    def _onchange_set_payment_token_id(self):
        res = {}

        if not self.payment_method_code == 'electronic' or not self.partner_id or not self.journal_id:
            self.payment_token_id = False
            return res

        partners = self.partner_id | self.partner_id.commercial_partner_id | self.partner_id.commercial_partner_id.child_ids
        domain = [('partner_id', 'in', partners.ids), ('acquirer_id.journal_id', '=', self.journal_id.id)]
        self.payment_token_id = self.env['payment.token'].search(domain, limit=1)

        res['domain'] = {'payment_token_id': domain}
        return res

    def _prepare_payment_transaction_vals(self):
        self.ensure_one()
        return {
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_country_id': self.partner_id.country_id.id,
            'invoice_ids': [(6, 0, self.invoice_ids.ids)],
            'payment_token_id': self.payment_token_id.id,
            'acquirer_id': self.payment_token_id.acquirer_id.id,
            'payment_id': self.id,
            'type': 'server2server',
        }

    def _create_payment_transaction(self, vals=None):
        for pay in self:
            if pay.payment_transaction_id:
                raise ValidationError(_('A payment transaction already exists.'))
            elif not pay.payment_token_id:
                raise ValidationError(_('A token is required to create a new payment transaction.'))

        transactions = self.env['payment.transaction']
        for pay in self:
            transaction_vals = pay._prepare_payment_transaction_vals()

            if vals:
                transaction_vals.update(vals)

            transaction = self.env['payment.transaction'].create(transaction_vals)
            transactions += transaction

            # Link the transaction to the payment.
            pay.payment_transaction_id = transaction

        return transactions

    def action_validate_invoice_payment(self):
        res = super(AccountPayment, self).action_validate_invoice_payment()
        self.mapped('payment_transaction_id').filtered(lambda x: x.state == 'done' and not x.is_processed)._post_process_after_done()
        return res

    def post(self):
        # Post the payments "normally" if no transactions are needed.
        # If not, let the acquirer updates the state.
        #                                __________            ______________
        #                               | Payments |          | Transactions |
        #                               |__________|          |______________|
        #                                  ||                      |    |
        #                                  ||                      |    |
        #                                  ||                      |    |
        #  __________  no s2s required   __\/______   s2s required |    | s2s_do_transaction()
        # |  Posted  |<-----------------|  post()  |----------------    |
        # |__________|                  |__________|<-----              |
        #                                                |              |
        #                                               OR---------------
        #  __________                    __________      |
        # | Cancelled|<-----------------| cancel() |<-----
        # |__________|                  |__________|

        payments_need_trans = self.filtered(lambda pay: pay.payment_token_id and not pay.payment_transaction_id)
        transactions = payments_need_trans._create_payment_transaction()

        res = super(AccountPayment, self - payments_need_trans).post()

        transactions.s2s_do_transaction()

        return res
