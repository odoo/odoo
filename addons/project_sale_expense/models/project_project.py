# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models, fields
from collections import defaultdict


class Project(models.Model):
    _inherit = 'project.project'

    def _get_expenses_profitability_items(self, with_action=True):
        if not self.analytic_account_id:
            return {}
        can_see_expense = with_action and self.user_has_groups('hr_expense.group_hr_expense_team_approver')
        query = self.env['hr.expense']._search([('state', 'in', ['approved', 'done'])])
        query.add_where('hr_expense.analytic_distribution ? %s', [str(self.analytic_account_id.id)])
        query_string, query_param = query.select('sale_order_id', 'product_id', 'currency_id', 'array_agg(id) as ids', 'SUM(untaxed_amount_currency) as untaxed_amount_currency')
        query_string = f"{query_string} GROUP BY sale_order_id, product_id, currency_id"
        self._cr.execute(query_string, query_param)
        expenses_read_group = [expense for expense in self._cr.dictfetchall()]
        if not expenses_read_group:
            return {}
        expenses_per_so_id = {}
        expense_ids = []
        amount_billed = 0.0
        today = fields.Date.context_today(self)
        convert_company = self.company_id or self.env.company
        dict_amount_per_currency = defaultdict(lambda: 0.0)
        for res in expenses_read_group:
            so_id = res['sale_order_id']
            product_id = res['product_id']
            expenses_per_so_id.setdefault(so_id, {})[product_id] = res['ids']
            if can_see_expense:
                expense_ids.extend(res['ids'])
            dict_amount_per_currency[res['currency_id']] += res['untaxed_amount_currency']
        for currency_id in dict_amount_per_currency:
            if currency_id == self.currency_id.id:
                amount_billed += dict_amount_per_currency[currency_id]
                continue
            currency = self.env['res.currency'].browse(currency_id)
            rate = currency._get_conversion_rate(currency, self.currency_id, convert_company, today)
            amount_billed += self.currency_id.round(dict_amount_per_currency[currency_id] * rate)

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
        rate_per_currency_id = {self.currency_id.id: 1}
        if len(set_currency_ids) > 1:
            rate_per_currency_id = self.env['res.currency'].browse(set_currency_ids)._get_rates(self.company_id or self.env.company, today)
        project_currency_rate = rate_per_currency_id[self.currency_id.id]
        for currency, revenues in dict_invoices_amount_per_currency.items():
            if currency.id == self.currency_id.id:
                total_amount_expense_to_invoice += revenues['to_invoice']
                total_amount_expense_invoiced += revenues['invoiced']
                continue
            rate = project_currency_rate / rate_per_currency_id[currency.id]
            total_amount_expense_to_invoice += self.currency_id.round(revenues['to_invoice'] * rate)
            total_amount_expense_invoiced += self.currency_id.round(revenues['invoiced'] * rate)

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
