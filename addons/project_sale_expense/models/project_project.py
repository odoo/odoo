# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models, fields
from collections import defaultdict


class Project(models.Model):
    _inherit = 'project.project'

    def _get_expenses_profitability_items(self, with_action=True):
        expenses_read_group = self.env['hr.expense']._read_group(
            [('sheet_id.state', 'in', ['post', 'done']), ('analytic_distribution', 'in', self.account_id.ids)],
            groupby=['sale_order_id', 'product_id', 'currency_id'],
            aggregates=['id:array_agg', 'untaxed_amount_currency:sum'],
        )
        if not expenses_read_group:
            return {}
        expenses_per_so_id = {}
        expense_ids = []
        dict_amount_per_currency = defaultdict(lambda: 0.0)
        can_see_expense = with_action and self.env.user.has_group('hr_expense.group_hr_expense_team_approver')
        for sale_order, product, currency, ids, untaxed_amount_currency_sum in expenses_read_group:
            expenses_per_so_id.setdefault(sale_order.id, {})[product.id] = ids
            if can_see_expense:
                expense_ids.extend(ids)
            dict_amount_per_currency[currency] += untaxed_amount_currency_sum

        amount_billed = 0.0
        for currency, untaxed_amount_currency_sum in dict_amount_per_currency.items():
            amount_billed += currency._convert(untaxed_amount_currency_sum, self.currency_id, self.company_id, round=False)

        sol_read_group = self.env['sale.order.line'].sudo()._read_group(
            [
                ('order_id', 'in', list(expenses_per_so_id.keys())),
                ('is_expense', '=', True),
                ('state', '=', 'sale'),
            ],
            ['order_id', 'product_id', 'currency_id'],
            ['untaxed_amount_to_invoice:sum', 'untaxed_amount_invoiced:sum'],
        )

        total_amount_expense_invoiced = total_amount_expense_to_invoice = 0.0
        reinvoice_expense_ids = []
        dict_invoices_amount_per_currency = defaultdict(lambda: {'to_invoice': 0.0, 'invoiced': 0.0})
        set_currency_ids = {self.currency_id.id}
        for order, product, currency, untaxed_amount_to_invoice_sum, untaxed_amount_invoiced_sum in sol_read_group:
            expense_data_per_product_id = expenses_per_so_id[order.id]
            set_currency_ids.add(currency.id)
            product_id = product.id
            if product_id in expense_data_per_product_id:
                dict_invoices_amount_per_currency[currency]['to_invoice'] += untaxed_amount_to_invoice_sum
                dict_invoices_amount_per_currency[currency]['invoiced'] += untaxed_amount_invoiced_sum
                reinvoice_expense_ids += expense_data_per_product_id[product_id]
        for currency, revenues in dict_invoices_amount_per_currency.items():
            total_amount_expense_to_invoice += currency._convert(revenues['to_invoice'], self.currency_id, self.company_id)
            total_amount_expense_invoiced += currency._convert(revenues['invoiced'], self.currency_id, self.company_id)

        section_id = 'expenses'
        sequence = self._get_profitability_sequence_per_invoice_type()[section_id]
        expense_data = {
            'costs': {
                'id': section_id,
                'sequence': sequence,
                'billed': -amount_billed,
                'to_bill': 0.0,
            },
        }
        if reinvoice_expense_ids:
            expense_data['revenues'] = {
                'id': section_id,
                'sequence': sequence,
                'invoiced': total_amount_expense_invoiced,
                'to_invoice': total_amount_expense_to_invoice,
            }
        if can_see_expense:
            def get_action(res_ids):
                args = [section_id, [('id', 'in', res_ids)]]
                if len(res_ids) == 1:
                    args.append(res_ids[0])
                return {'name': 'action_profitability_items', 'type': 'object', 'args': json.dumps(args)}

            if reinvoice_expense_ids:
                expense_data['revenues']['action'] = get_action(reinvoice_expense_ids)
            if expense_ids:
                expense_data['costs']['action'] = get_action(expense_ids)
        return expense_data
