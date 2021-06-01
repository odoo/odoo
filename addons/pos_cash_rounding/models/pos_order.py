# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.tools import float_is_zero, float_round

class PosOrder(models.Model):
    _inherit = "pos.order"


    def _get_rounded_amount(self, amount):
        if self.config_id.cash_rounding and (
                not self.config_id.only_round_cash_method or self.payment_ids.filtered(lambda p: p.payment_method_id.is_cash_count)):
            amount = float_round(amount, precision_rounding=self.config_id.rounding_method.rounding, rounding_method=self.config_id.rounding_method.rounding_method)
        return super(PosOrder, self)._get_rounded_amount(amount)

    def _prepare_invoice_vals(self):
        vals = super(PosOrder, self)._prepare_invoice_vals()
        if self.config_id.cash_rounding and (
                not self.config_id.only_round_cash_method or self.payment_ids.filtered(lambda p: p.payment_method_id.is_cash_count)):
            vals['invoice_cash_rounding_id'] = self.config_id.rounding_method.id
        return vals

    def _create_invoice(self, move_vals):
        new_move = super(PosOrder, self)._create_invoice(move_vals)
        if self.config_id.cash_rounding:
            rounding_applied = float_round(self.amount_paid - self.amount_total, precision_rounding=new_move.currency_id.rounding)
            rounding_line = new_move.line_ids.filtered(lambda line: line.is_rounding_line)
            if rounding_line and rounding_line.debit > 0:
                rounding_line_difference = rounding_line.debit + rounding_applied
            elif rounding_line and rounding_line.credit > 0:
                rounding_line_difference = -rounding_line.credit + rounding_applied
            else:
                rounding_line_difference = rounding_applied
            if rounding_applied:
                if rounding_applied > 0.0:
                    account_id = new_move.invoice_cash_rounding_id._get_loss_account_id().id
                else:
                    account_id = new_move.invoice_cash_rounding_id._get_profit_account_id().id
                if rounding_line:
                    if rounding_line_difference:
                        rounding_line.with_context(check_move_validity=False).write({
                            'debit': rounding_applied < 0.0 and -rounding_applied or 0.0,
                            'credit': rounding_applied > 0.0 and rounding_applied or 0.0,
                            'account_id': account_id,
                            'price_unit': rounding_applied,
                        })
                else:
                    self.env['account.move.line'].with_context(check_move_validity=False).create({
                         'debit': rounding_applied < 0.0 and -rounding_applied or 0.0,
                         'credit': rounding_applied > 0.0 and rounding_applied or 0.0,
                         'quantity': 1.0,
                         'amount_currency': rounding_applied,
                         'partner_id': new_move.partner_id.id,
                         'move_id': new_move.id,
                         'currency_id': new_move.currency_id if new_move.currency_id != new_move.company_id.currency_id else False,
                         'company_id': new_move.company_id.id,
                         'company_currency_id': new_move.company_id.currency_id.id,
                         'is_rounding_line': True,
                         'sequence': 9999,
                         'name': new_move.invoice_cash_rounding_id.name,
                         'account_id': account_id,
                     })
            else:
                if rounding_line:
                    rounding_line.with_context(check_move_validity=False).unlink()
            if rounding_line_difference:
                existing_terms_line = new_move.line_ids.filtered(
                    lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                if existing_terms_line.debit > 0:
                    existing_terms_line_new_val = float_round(
                        existing_terms_line.debit + rounding_line_difference,
                        precision_rounding=new_move.currency_id.rounding)
                else:
                    existing_terms_line_new_val = float_round(
                        -existing_terms_line.credit + rounding_line_difference,
                        precision_rounding=new_move.currency_id.rounding)
                existing_terms_line.write({
                    'debit': existing_terms_line_new_val > 0.0 and existing_terms_line_new_val or 0.0,
                    'credit': existing_terms_line_new_val < 0.0 and -existing_terms_line_new_val or 0.0,
                })

                new_move._recompute_payment_terms_lines()
        return new_move

    def _get_amount_receivable(self):
        if self.config_id.cash_rounding and (
                not self.config_id.only_round_cash_method or self.payment_ids.filtered(lambda p: p.payment_method_id.is_cash_count)):
            return self.amount_paid
        return super(PosOrder, self)._get_amount_receivable()

    def _is_pos_order_paid(self):
        res = super(PosOrder, self)._is_pos_order_paid()
        if not res and self.config_id.cash_rounding:
            currency = self.currency_id
            if self.config_id.rounding_method.rounding_method == "HALF-UP":
                maxDiff = currency.round(self.config_id.rounding_method.rounding / 2)
            else:
                maxDiff = currency.round(self.config_id.rounding_method.rounding)

            diff = currency.round(self.amount_total - self.amount_paid)
            res = abs(diff) < maxDiff
        return res
