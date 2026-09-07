# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    display_type = fields.Selection(selection_add=[('advance_tax', 'Advance Tax')],
        ondelete={'advance_tax': 'cascade'})

    @api.model
    def _get_payment_tax_reverse_moves_line_vals(self, partial_line, payment_line_with_tax):
        line_vals = []
        sign = 1 if payment_line_with_tax.balance < 0 else -1
        payment_amount = payment_line_with_tax.payment_id.amount
        base_amount = (payment_amount / partial_line.amount) * partial_line.amount
        compute_all_res = payment_line_with_tax.payment_id.tax_ids.with_context(force_price_include=True).compute_all(base_amount, currency=partial_line.company_currency_id)
        for tax_res in compute_all_res['taxes']:
            amount = tax_res['amount'] * sign
            line_vals.append(Command.create({
                'name': tax_res['name'],
                'account_id': tax_res['account_id'],
                'partner_id': payment_line_with_tax.partner_id.id,
                'debit': amount if amount > 0.0 else 0.0,
                'credit': -amount if amount < 0.0 else 0.0,
                'tax_tag_ids': tax_res['tag_ids'],
                'display_type': 'advance_tax'
            }))
        total_tax_amount = (compute_all_res['total_included'] - compute_all_res['total_excluded']) * sign * -1
        line_vals.append(Command.create({
            'name': "Tax Adjustment Counter Part",
            'account_id': partial_line.company_id.account_advance_payment_tax_account_id.id,
            'partner_id': payment_line_with_tax.partner_id.id,
            'debit': total_tax_amount if total_tax_amount > 0.0 else 0.0,
            'credit': -total_tax_amount if total_tax_amount < 0.0 else 0.0,
            'display_type': 'advance_tax'
        }))
        return line_vals

    @api.model
    def _get_payment_tax_reverse_moves_vals(self, partial_line, payment_line_with_tax):
        return {
            'move_type': 'entry',
            'partner_id': payment_line_with_tax.partner_id.id,
            'tax_advanced_adjust_rec_id': partial_line.id,
            'ref': _('Advanced Payment Tax Adjustment of %s - %s', partial_line.credit_move_id.move_id.name, partial_line.debit_move_id.move_id.name),
            'journal_id': partial_line.company_id.account_advance_payment_tax_adjustment_journal_id.id,
            'line_ids': self._get_payment_tax_reverse_moves_line_vals(partial_line, payment_line_with_tax),
            'advanced_payment_tax_origin_move_id': payment_line_with_tax.payment_id.move_id.id,
        }

    def reconcile(self):
        result = super().reconcile()
        for line in result.get('partials', self.env['account.partial.reconcile']):
            reconcile_lines = line.credit_move_id + line.debit_move_id
            payment_line_with_tax = reconcile_lines.filtered(lambda l: l.payment_id.tax_ids)
            reconcile_with_invoice_or_bill = reconcile_lines.filtered(lambda l: l.move_id.is_invoice(include_receipts=True)).move_id
            if payment_line_with_tax and reconcile_with_invoice_or_bill:
                result.setdefault('advanced_tax_adjustments', {})
                move = self.env['account.move'].create(self._get_payment_tax_reverse_moves_vals(line, payment_line_with_tax))
                move.action_post()
                result['advanced_tax_adjustments'][line.id] = move
        return result
