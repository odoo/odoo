# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # == Business fields ==
    payment_transaction_id = fields.Many2one(
        string="Payment Transaction", comodel_name='payment.transaction', readonly=True)
    payment_token_id = fields.Many2one(
        string="Saved Payment Token", comodel_name='payment.token', domain="""[
            ('id', 'in', suitable_payment_token_ids),
        ]""",
        help="Note that only tokens from acquirers allowing to capture the amount are available.")

    # == Display purpose fields ==
    suitable_payment_token_ids = fields.Many2many(
        comodel_name='payment.token',
        compute='_compute_suitable_payment_token_ids'
    )
    use_electronic_payment_method = fields.Boolean(
        compute='_compute_use_electronic_payment_method',
        help='Technical field used to hide or show the payment_token_id if needed.'
    )

    @api.depends('payment_method_line_id')
    def _compute_suitable_payment_token_ids(self):
        for payment in self:
            related_partner_ids = (
                    payment.partner_id
                    | payment.partner_id.commercial_partner_id
                    | payment.partner_id.commercial_partner_id.child_ids
            )._origin

            if payment.use_electronic_payment_method:
                payment.suitable_payment_token_ids = self.env['payment.token'].sudo().search([
                    ('company_id', '=', payment.company_id.id),
                    ('acquirer_id.capture_manually', '=', False),
                    ('partner_id', 'in', related_partner_ids.ids),
                    ('acquirer_id', '=', payment.payment_method_line_id.payment_acquirer_id.id),
                ])
            else:
                payment.suitable_payment_token_ids = [Command.clear()]

    @api.depends('payment_method_line_id')
    def _compute_use_electronic_payment_method(self):
        for payment in self:
            # Get a list of all electronic payment method codes.
            # These codes are comprised of 'electronic' and the providers of each payment acquirer.
            codes = [key for key in dict(self.env['payment.acquirer']._fields['provider']._description_selection(self.env))]
            payment.use_electronic_payment_method = payment.payment_method_code in codes

    @api.onchange('partner_id', 'payment_method_line_id', 'journal_id')
    def _onchange_set_payment_token_id(self):
        codes = [key for key in dict(self.env['payment.acquirer']._fields['provider']._description_selection(self.env))]
        if not (self.payment_method_code in codes and self.partner_id and self.journal_id):
            self.payment_token_id = False
            return

        related_partner_ids = (
                self.partner_id
                | self.partner_id.commercial_partner_id
                | self.partner_id.commercial_partner_id.child_ids
        )._origin

        self.payment_token_id = self.env['payment.token'].sudo().search([
            ('company_id', '=', self.company_id.id),
            ('partner_id', 'in', related_partner_ids.ids),
            ('acquirer_id.capture_manually', '=', False),
            ('acquirer_id', '=', self.payment_method_line_id.payment_acquirer_id.id),
         ], limit=1)

    def _get_payment_chatter_link(self):
        self.ensure_one()
        return f'<a href=# data-oe-model=account.payment data-oe-id={self.id}>{self.name}</a>'

    def _create_payment_transaction(self, **extra_create_values):
        for payment in self:
            if payment.payment_transaction_id:
                raise ValidationError(_(
                    "A payment transaction with reference %s already exists.",
                    payment.payment_transaction_id.reference
                ))
            elif not payment.payment_token_id:
                raise ValidationError(_("A token is required to create a new payment transaction."))

        # Transactions in sudo to read acquirer fields.
        transactions = self.env['payment.transaction'].sudo()
        for payment in self:
            transaction_vals = payment._prepare_payment_transaction_vals(**extra_create_values)
            transaction = transactions.create(transaction_vals)
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
        # Create the missing payment transactions.
        payments_needing_tx = self.filtered(lambda pay: pay.payment_token_id and not pay.payment_transaction_id)
        payments_needing_tx._create_payment_transaction()

        # Process payment transactions directly.
        transactions_needing_request = self.filtered('payment_transaction_id').payment_transaction_id
        for tx in transactions_needing_request:
            tx._send_payment_request()

        # Post payments.
        payments_to_post = self.filtered(lambda pay: not pay.payment_transaction_id
                                                     or pay.payment_transaction_id.state == 'done')
        res = super(AccountPayment, payments_to_post).action_post()

        # Post-process transactions.
        transactions_done = payments_needing_tx.payment_transaction_id.filtered(lambda x: x.state == 'done')
        transactions_done._finalize_post_processing()

        # Cancel payments if the payment transactions failed.
        payments_to_cancel = payments_needing_tx.payment_transaction_id.filtered(lambda x: x.state != 'done').payment_id
        payments_to_cancel.action_cancel()

        return res
