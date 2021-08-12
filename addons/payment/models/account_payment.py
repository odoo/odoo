# coding: utf-8

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_transaction_id = fields.Many2one('payment.transaction', string='Payment Transaction', readonly=True)
    payment_token_id = fields.Many2one(
        'payment.token', string="Saved payment token",
        domain="""[
            (payment_method_code == 'electronic', '=', 1),
            ('company_id', '=', company_id),
            ('acquirer_id.capture_manually', '=', False),
            ('acquirer_id.journal_id', '=', journal_id),
            ('partner_id', 'in', related_partner_ids),
        ]""",
        help="Note that tokens from acquirers set to only authorize transactions (instead of capturing the amount) are not available.")
    related_partner_ids = fields.Many2many('res.partner', compute='_compute_related_partners')

    def _get_payment_chatter_link(self):
        self.ensure_one()
        return '<a href=# data-oe-model=account.payment data-oe-id=%d>%s</a>' % (self.id, self.name)

    @api.depends('partner_id.commercial_partner_id.child_ids')
    def _compute_related_partners(self):
        for p in self:
            p.related_partner_ids = (
                p.partner_id
              | p.partner_id.commercial_partner_id
              | p.partner_id.commercial_partner_id.child_ids
            )._origin

    @api.onchange('partner_id', 'payment_method_id', 'journal_id')
    def _onchange_set_payment_token_id(self):
        if not (self.payment_method_code == 'electronic' and self.partner_id and self.journal_id):
            self.payment_token_id = False
            return

        self.payment_token_id = self.env['payment.token'].search([
            ('partner_id', 'in', self.related_partner_ids.ids),
            ('acquirer_id.capture_manually', '=', False),
            ('acquirer_id.journal_id', '=', self.journal_id.id),
         ], limit=1)

    def _prepare_payment_transaction_vals(self):
        self.ensure_one()
        return {
            'amount': self.amount,
            'reference': self.ref,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_country_id': self.partner_id.country_id.id,
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

    def action_post(self):
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

        # Create the missing payment transactions.
        payments_need_trans = self.filtered(lambda pay: pay.payment_token_id and not pay.payment_transaction_id)
        payments_need_trans._create_payment_transaction()

        # Process payment transactions directly.
        payments_with_trans = self.filtered('payment_transaction_id')
        transactions = payments_with_trans.payment_transaction_id
        transactions.s2s_do_transaction()

        # Post payments.
        payments_to_post = self.filtered(lambda pay: not pay.payment_transaction_id
                                                     or pay.payment_transaction_id.state == 'done')
        res = super(AccountPayment, payments_to_post).action_post()

        # Post process transactions.
        transactions = payments_need_trans.payment_transaction_id.filtered(lambda x: x.state == 'done')
        transactions._post_process_after_done()

        # Cancel payments if the payment transactions failed.
        payments_to_cancel = payments_need_trans.payment_transaction_id.filtered(lambda x: x.state != 'done').payment_id
        payments_to_cancel.action_cancel()

        return res
