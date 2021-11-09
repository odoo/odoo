# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # == Business fields ==
    payment_transaction_id = fields.Many2one(
        string="Payment Transaction",
        comodel_name='payment.transaction',
        readonly=True,
        auto_join=True,  # No access rule bypass since access to payments means access to txs too
    )
    payment_token_id = fields.Many2one(
        string="Saved Payment Token", comodel_name='payment.token', domain="""[
            ('id', 'in', suitable_payment_token_ids),
        ]""",
        help="Note that only tokens from acquirers allowing to capture the amount are available.")
    amount_available_for_refund = fields.Monetary(compute='_compute_amount_available_for_refund')

    # == Display purpose fields ==
    suitable_payment_token_ids = fields.Many2many(
        comodel_name='payment.token',
        compute='_compute_suitable_payment_token_ids'
    )
    use_electronic_payment_method = fields.Boolean(
        compute='_compute_use_electronic_payment_method',
        help='Technical field used to hide or show the payment_token_id if needed.'
    )

    # == Fields used for traceability ==
    source_payment_id = fields.Many2one(
        string="Source Payment",
        comodel_name='account.payment',
        help="The source payment of related refund payments",
        related='payment_transaction_id.source_transaction_id.payment_id',
        readonly=True,
        store=True,  # Stored for the group by in `_compute_refunds_count`
    )
    refunds_count = fields.Integer(string="Refunds Count", compute='_compute_refunds_count')

    def _compute_amount_available_for_refund(self):
        for payment in self:
            tx = payment.payment_transaction_id
            if tx.acquirer_id.sudo().support_refund and tx.operation != 'refund':
                # Only consider refund transactions that are confirmed by summing the amounts of
                # payments linked to such refund transactions. Indeed, should a refund transaction
                # be stuck forever in a transient state (due to webhook failure, for example), the
                # user would never be allowed to refund the source transaction again.
                refund_payments = self.search([('source_payment_id', '=', self.id)])
                refunded_amount = abs(sum(refund_payments.mapped('amount')))
                payment.amount_available_for_refund = payment.amount - refunded_amount
            else:
                payment.amount_available_for_refund = 0

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

    def _compute_refunds_count(self):
        rg_data = self.env['account.payment'].read_group(
            domain=[
                ('source_payment_id', 'in', self.ids),
                ('payment_transaction_id.operation', '=', 'refund')
            ],
            fields=['source_payment_id'],
            groupby=['source_payment_id']
        )
        data = {x['source_payment_id'][0]: x['source_payment_id_count'] for x in rg_data}
        for payment in self:
            payment.refunds_count = data.get(payment.id, 0)

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

    def action_post(self):
        # Post the payments "normally" if no transactions are needed.
        # If not, let the acquirer update the state.

        payments_need_tx = self.filtered(
            lambda p: p.payment_token_id and not p.payment_transaction_id
        )
        # creating the transaction require to access data on payment acquirers, not always accessible to users
        # able to create payments
        transactions = payments_need_tx.sudo()._create_payment_transaction()

        res = super(AccountPayment, self - payments_need_tx).action_post()

        for tx in transactions:  # Process the transactions with a payment by token
            tx._send_payment_request()

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

    def action_refund_wizard(self):
        self.ensure_one()
        return {
            'name': _("Refund"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.refund.wizard',
            'target': 'new',
        }

    def action_view_refunds(self):
        self.ensure_one()
        action = {
            'name': _("Refund"),
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
        }
        if self.refunds_count == 1:
            refund_tx = self.env['account.payment'].search([
                ('source_payment_id', '=', self.id)
            ], limit=1)
            action['res_id'] = refund_tx.id
            action['view_mode'] = 'form'
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('source_payment_id', '=', self.id)]
        return action

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
