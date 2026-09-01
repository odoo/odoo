# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    use_sale_order_payment = fields.Boolean(
        string='Use SO Payment',
        help="When enabled, this payment method represents an online payment already "
         "collected on a Sale Order. No actual payment is collected at the Point of Sale."
    )

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['use_sale_order_payment']

    @api.ondelete(at_uninstall=False)
    def _unlink_if_sale_order_payment_method(self):
        if any(pm.use_sale_order_payment for pm in self):
            raise ValidationError(
                _('You cannot delete this payment method because it is reserved for prepaid sale order payments.')
            )

    def _get_sale_order_payments(self, session):
        """POS payments of the session settled by this method.

        Only the ones backed by an accounting payment, since that payment is what the
        transfer moves to the POS receivable.
        """
        non_invoiced_orders = session._get_invoiced_and_non_invoiced_orders()[0]
        return non_invoiced_orders.payment_ids.filtered(
            lambda payment: payment.payment_method_id == self and payment.online_account_payment_id,
        )

    def _create_payment_line(self, session, amount, account=None, message=None, partner=None):
        if self.use_sale_order_payment:
            return self._create_sale_order_payment_line_transfer(session)
        return super()._create_payment_line(session, amount, account, message, partner)

    def _create_sale_order_payment_line_transfer(self, session):
        """Return the lines the session move reconciles the pre-paid amounts against.

        The customer paid on the sale order, so the account.payment already exists:
        unlike a bank payment method we must not create a new one. That payment credited
        its destination account, and two cases follow:

          - it already credited the POS receivable, so its own line is what the
            payment_term line of the session move reconciles with, and nothing has
            to be booked;
          - it credited another account (a dedicated customer receivable), so the amount
            is transferred to the POS receivable first:

              - Debit: destination account of the existing accounting payment
              - Credit: POS receivable
        """
        self.ensure_one()
        pos_receivable = session._get_receivable_account()

        settled_lines = self.env['account.move.line']
        amount_per_account = defaultdict(float)
        partner_per_account = {}
        for payment in self._get_sale_order_payments(session):
            account_payment = payment.online_account_payment_id
            account = account_payment.destination_account_id
            if account == pos_receivable:
                settled_lines |= account_payment.move_id.line_ids.filtered(
                    lambda line: line.account_id == pos_receivable,
                )
                continue
            amount_per_account[account] += payment.amount
            partner_per_account.setdefault(account, account_payment.partner_id)

        total_amount = sum(amount_per_account.values())
        if not total_amount:
            return settled_lines

        line_commands = [
            Command.create({
                'account_id': account.id,
                'debit': amount if amount > 0 else 0.0,
                'credit': -amount if amount < 0 else 0.0,
                'name': _('Sale Order Online Payment Transfer'),
                'partner_id': partner_per_account[account].id,
            })
            for account, amount in amount_per_account.items()
        ]
        line_commands.append(Command.create({
            'account_id': pos_receivable.id,
            'debit': -total_amount if total_amount < 0 else 0.0,
            'credit': total_amount if total_amount > 0 else 0.0,
            'name': _('POS Receivable Transfer'),
        }))

        transfer_move = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'journal_id': session.config_id.journal_id.id,
            'ref': _(
                'Transfer settled Sale Orders => %(pos_receivable_name)s',
                pos_receivable_name=pos_receivable.name,
            ),
            'line_ids': line_commands,
        })
        transfer_move._post()
        # amount_per_account never holds pos_receivable, so this matches only the
        # counterpart line appended above.
        return settled_lines | transfer_move.line_ids.filtered(
            lambda line: line.account_id == pos_receivable,
        )
