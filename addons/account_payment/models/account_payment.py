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
        bypass_search_access=True,  # No access rule bypass since access to payments means access to txs too
    )
    amount_available_for_refund = fields.Monetary(compute='_compute_amount_available_for_refund')

    # == Fields used for traceability ==
    source_payment_id = fields.Many2one(
        string="Source Payment",
        comodel_name='account.payment',
        help="The source payment of related refund payments",
        related='payment_transaction_id.source_transaction_id.payment_id',
        readonly=True,
        store=True,  # Stored for the group by in `_compute_refunds_count`
        index='btree_not_null',
    )
    refunds_count = fields.Integer(string="Refunds Count", compute='_compute_refunds_count')

    #=== COMPUTE METHODS ===#

    def _compute_amount_available_for_refund(self):
        for payment in self:
            tx_sudo = payment.payment_transaction_id.sudo()
            payment_method = (
                tx_sudo.payment_method_id.primary_payment_method_id
                or tx_sudo.payment_method_id
            )
            if (
                tx_sudo  # The payment was created by a transaction.
                and tx_sudo.provider_id.support_refund != 'none'
                and payment_method.support_refund != 'none'
                and tx_sudo.operation != 'refund'
            ):
                # Only consider refund transactions that are confirmed by summing the amounts of
                # payments linked to such refund transactions. Indeed, should a refund transaction
                # be stuck forever in a transient state (due to webhook failure, for example), the
                # user would never be allowed to refund the source transaction again.
                refund_payments = self.search([('source_payment_id', '=', payment.id)])
                refunded_amount = abs(sum(refund_payments.mapped('amount')))
                payment.amount_available_for_refund = payment.amount - refunded_amount
            else:
                payment.amount_available_for_refund = 0

    def _compute_refunds_count(self):
        rg_data = self.env['account.payment']._read_group(
            domain=[
                ('source_payment_id', 'in', self.ids),
                ('payment_transaction_id.operation', '=', 'refund')
            ],
            groupby=['source_payment_id'],
            aggregates=['__count']
        )
        data = {source_payment.id: count for source_payment, count in rg_data}
        for payment in self:
            payment.refunds_count = data.get(payment.id, 0)

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
            action['view_mode'] = 'list,form'
            action['domain'] = [('source_payment_id', '=', self.id)]
        return action

    def _get_payment_refund_wizard_values(self):
        self.ensure_one()
        return {
            'transaction_id': self.payment_transaction_id.id,
            'payment_amount': self.amount,
            'amount_available_for_refund': self.amount_available_for_refund,
        }
