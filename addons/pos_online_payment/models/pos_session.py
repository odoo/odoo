# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import models, tools, _
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _accumulate_amounts(self, data):
        data = super()._accumulate_amounts(data)
        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}

        split_receivables_online = defaultdict(amounts)
        currency_rounding = self.currency_id.rounding
        for order in self._get_closed_orders():
            for payment in order.payment_ids:
                amount = payment.amount
                if tools.float_is_zero(amount, precision_rounding=currency_rounding):
                    continue
                date = payment.payment_date
                payment_method = payment.payment_method_id
                payment_type = payment_method.type

                if payment_type == 'online':
                    split_receivables_online[payment] = self._update_amounts(split_receivables_online[payment], {'amount': amount}, date)

        data.update({'split_receivables_online': split_receivables_online,})
        return data

    def _create_bank_payment_moves(self, data):
        data = super()._create_bank_payment_moves(data)

        split_receivables_online = data.get('split_receivables_online')
        MoveLine = data.get('MoveLine')

        online_payment_to_receivable_lines = {}

        for payment, amounts in split_receivables_online.items():
            split_receivable_line = MoveLine.create(self._get_split_receivable_op_vals(payment, amounts['amount'], amounts['amount_converted']))
            account_payment = payment.online_account_payment_id
            payment_receivable_line = account_payment.move_id.line_ids.filtered(lambda line: line.account_id == account_payment.destination_account_id)
            online_payment_to_receivable_lines[payment] = split_receivable_line | payment_receivable_line

        data['online_payment_to_receivable_lines'] = online_payment_to_receivable_lines
        return data

    def _get_split_receivable_op_vals(self, payment, amount, amount_converted):
        partner = payment.online_account_payment_id.partner_id
        accounting_partner = self.env["res.partner"]._find_accounting_partner(partner)
        if not accounting_partner:
            raise UserError(_("The partner of the POS online payment (id=%d) could not be found", payment.id))
        partial_vals = {
            'account_id': accounting_partner.property_account_receivable_id.id,
            'move_id': self.move_id.id,
            'partner_id': accounting_partner.id,
            'name': '%s - %s (%s)' % (self.name, payment.payment_method_id.name, payment.online_account_payment_id.payment_method_line_id.payment_provider_id.name),
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _reconcile_account_move_lines(self, data):
        data = super()._reconcile_account_move_lines(data)
        online_payment_to_receivable_lines = data.get('online_payment_to_receivable_lines')

        for payment, lines in online_payment_to_receivable_lines.items():
            if payment.online_account_payment_id.partner_id.property_account_receivable_id.reconcile:
                lines.filtered(lambda line: not line.reconciled).reconcile()

        return data
