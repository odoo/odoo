# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.tools import float_is_zero, float_round, float_compare

class PosOrder(models.Model):
    _inherit = "pos.order"


    def test_paid(self):
        if self.config_id.cash_rounding:
            total = float_round(self.amount_total, precision_rounding=self.config_id.rounding_method.rounding, rounding_method=self.config_id.rounding_method.rounding_method)
            return float_is_zero(total - self.amount_paid, precision_rounding=self.config_id.currency_id.rounding)
        else:
            return super(PosOrder, self).test_paid()

    def _prepare_invoice(self):
        vals = super(PosOrder, self)._prepare_invoice()
        vals['cash_rounding_id'] = self.config_id.rounding_method.id if self.config_id.cash_rounding else False
        return vals

    def _create_invoice(self):
        invoice = super(PosOrder, self)._create_invoice()
        if invoice.cash_rounding_id:
            invoice._onchange_cash_rounding()
        return invoice


    def _get_amount_receivable(self, move_lines):
        if self.config_id.cash_rounding:
            res = {}
            cur = self.pricelist_id.currency_id
            cur_company = self.company_id.currency_id
            if cur != cur_company:
                date_order = date_order = self.date_order.date() if self.date_order else fields.Date.today()
                amount = cur._convert(self.amount_paid, cur_company, self.company_id, date_order)
                res['amount'] = amount
                res['amount_currency'] = self.amount_paid
            else:
                res['amount'] = self.amount_paid
                res['amount_currency'] = False
            return res
        else:
            return super(PosOrder, self)._get_amount_receivable(move_lines)

    def _prepare_account_move_and_lines(self, session=None, move=None):
        res = super(PosOrder, self)._prepare_account_move_and_lines(session, move)
        unpaid_order = self.filtered(lambda o: o.account_move.id == res['move'].id)
        if unpaid_order:
            config_id = unpaid_order[0].config_id
            if config_id.cash_rounding and config_id.rounding_method:
                difference = 0.0
                converted_amount = 0.0
                config_id = unpaid_order[0].config_id
                company_id = unpaid_order[0].company_id
                different_currency = config_id.currency_id if config_id.currency_id.id != company_id.currency_id.id else False
                for order in unpaid_order:
                    order_difference = order.amount_paid - order.amount_total
                    difference += order_difference
                    if config_id.currency_id.id != company_id.currency_id.id:
                        converted_paid = different_currency._convert(order.amount_paid,  company_id.currency_id, company_id, order.date_order)
                        converted_total = different_currency._convert(order.amount_total,  company_id.currency_id, company_id, order.date_order)
                        converted_amount += converted_paid - converted_total
                    else:
                        converted_amount += order_difference
                if difference:
                    profit_account = config_id.rounding_method._get_profit_account_id().id
                    loss_account = config_id.rounding_method._get_loss_account_id().id
                    difference_move_line = {
                        'name': 'Rounding Difference',
                        'partner_id': False,
                        'move_id': res['move'].id,
                    }
                    grouped_data_key = False
                    if float_compare(0.0, difference, precision_rounding=config_id.currency_id.rounding) > 0:
                        difference_move_line.update({
                            'account_id': loss_account,
                            'credit': 0.0,
                            'debit': -converted_amount,
                        })
                        if different_currency:
                            difference_move_line.update({
                                'currency_id': different_currency.id,
                                'amount_currency': -difference
                            })
                        grouped_data_key = ('difference_rounding',
                                False,
                                loss_account,
                                True,
                                different_currency.id if different_currency else False)
                    if float_compare(0.0, difference, precision_rounding=config_id.currency_id.rounding) < 0:
                        difference_move_line.update({
                            'account_id': profit_account,
                            'credit': converted_amount,
                            'debit': 0.0,
                        })
                        if different_currency:
                            difference_move_line.update({
                                'currency_id': different_currency.id,
                                'amount_currency': difference
                            })
                        grouped_data_key = ('difference_rounding',
                                False,
                                profit_account,
                                False,
                                different_currency.id if different_currency else False)
                    if grouped_data_key:
                        res['grouped_data'][grouped_data_key] = [difference_move_line]
        return res
