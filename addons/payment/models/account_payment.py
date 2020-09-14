# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_transaction_id = fields.Many2one(
        string="Payment Transaction", comodel_name='payment.transaction', readonly=True)
    payment_token_id = fields.Many2one(
        string="Saved Payment Token", comodel_name='payment.token', domain="""[
            (payment_method_code == 'electronic', '=', 1),
            ('company_id', '=', company_id),
            ('acquirer_id.capture_manually', '=', False),
            ('acquirer_id.journal_id', '=', journal_id),
            ('partner_id', 'in', related_partner_ids),
        ]""",
        help="Note that only tokens from acquirers allowing to capture the amount are available.")
    related_partner_ids = fields.Many2many(
        comodel_name='res.partner', compute='_compute_related_partners')

    @api.depends('partner_id.commercial_partner_id.child_ids')
    def _compute_related_partners(self):
        for payment in self:
            payment.related_partner_ids = (
                    payment.partner_id
                    | payment.partner_id.commercial_partner_id
                    | payment.partner_id.commercial_partner_id.child_ids
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

    def _get_payment_chatter_link(self):
        self.ensure_one()
        return f'<a href=# data-oe-model=account.payment data-oe-id={self.id}>{self.name}</a>'

    def _create_payment_transaction(self, **extra_create_values):
        for payment in self:
            if payment.payment_transaction_id:
                raise ValidationError(_("A payment transaction already exists."))
            elif not payment.payment_token_id:
                raise ValidationError(_("A token is required to create a new payment transaction."))

        transactions = self.env['payment.transaction']
        for payment in self:
            transaction_vals = payment._prepare_payment_transaction_vals(**extra_create_values)
            transaction = self.env['payment.transaction'].create(transaction_vals)
            transactions += transaction
            payment.payment_transaction_id = transaction  # Link the transaction to the payment
        return transactions

    def _prepare_payment_transaction_vals(self, **extra_create_values):
        self.ensure_one()
        return {
            'acquirer_id': self.payment_token_id.acquirer_id.id,
            'reference': self.ref,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'token_id': self.payment_token_id.id,
            'operation': 'offline',
            'payment_id': self.id,
            **extra_create_values,
        }

    def action_post(self):
        # Post the payments "normally" if no transactions are needed.
        # If not, let the acquirer update the state.

        payments_need_tx = self.filtered(
            lambda p: p.payment_token_id and not p.payment_transaction_id
        )
        transactions = payments_need_tx._create_payment_transaction()

        res = super(AccountPayment, self - payments_need_tx).action_post()

        transactions._send_payment_request()  # Process the transactions with a payment by token

        # Post payments for issued transactions
        transactions._finalize_post_processing()
        payments_tx_done = payments_need_tx.filtered(
            lambda p: p.payment_transaction_id.state == 'done'
        )
        super(AccountPayment, payments_tx_done).action_post()
        payments_tx_not_done = payments_need_tx.filtered(
            lambda p: p.payment_transaction_id.state != 'done'
        )
        payments_tx_not_done.action_cancel()

        return res
