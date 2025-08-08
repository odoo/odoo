# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from collections import defaultdict

from odoo import models, _lt
from odoo.tools import SQL
from odoo.tools.misc import OrderedSet


class Project(models.Model):
    _inherit = 'project.project'

    def _add_purchase_items(self, profitability_items, with_action=True):
        domain = self._get_add_purchase_items_domain()
        with_action = with_action and self.user_has_groups('account.group_account_invoice, account.group_account_readonly')
        self._get_costs_items_from_purchase(domain, profitability_items, with_action=with_action)

    def _get_add_purchase_items_domain(self):
        purchase_order_line_invoice_line_ids = self._get_already_included_profitability_invoice_line_ids()
        return [
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('parent_state', 'in', ['draft', 'posted']),
            ('price_subtotal', '>', 0),
            ('id', 'not in', purchase_order_line_invoice_line_ids),
        ]

    def _get_costs_items_from_purchase(self, domain, profitability_items, with_action=True):
        """ This method is used in sale_project and project_purchase. Since project_account is the only common module (except project), we create the method here. """
        # calculate the cost of bills without a purchase order
        query = self.env['account.move.line'].sudo()._search(domain)
        query.add_where(
            SQL(
                "%s && %s",
                [str(self.analytic_account_id.id)],
                self.env['account.move.line'].sudo()._query_analytic_accounts(),
            )
        )
        query_string, query_param = query.select('balance', 'parent_state', 'account_move_line.company_currency_id', 'account_move_line.analytic_distribution', 'move_id', 'account_move_line.date')
        self._cr.execute(query_string, query_param)
        bills_move_line_read = self._cr.dictfetchall()
        if bills_move_line_read:
            # Get conversion rate from currencies to currency of the current company
            currency_ids = OrderedSet(bml['company_currency_id'] for bml in bills_move_line_read)
            amount_invoiced = amount_to_invoice = 0.0
            move_ids = set()
            for moves_read in bills_move_line_read:
                line_balance = self.env['res.currency'].browse(moves_read['company_currency_id']).with_prefetch(currency_ids)._convert(
                    from_amount=moves_read['balance'], to_currency=self.currency_id, date=moves_read['date']
                )
                # an analytic account can appear several time in an analytic distribution with different repartition percentage
                analytic_contribution = sum(
                    percentage for ids, percentage in moves_read['analytic_distribution'].items()
                    if str(self.analytic_account_id.id) in ids.split(',')
                ) / 100.
                move_ids.add(moves_read['move_id'])
                if moves_read['parent_state'] == 'draft':
                    amount_to_invoice -= line_balance * analytic_contribution
                else:  # moves_read['parent_state'] == 'posted'
                    amount_invoiced -= line_balance * analytic_contribution
            # don't display the section if the final values are both 0 (bill -> vendor credit)
            if amount_invoiced != 0 or amount_to_invoice != 0:
                costs = profitability_items['costs']
                section_id = 'other_purchase_costs'
                bills_costs = {
                    'id': section_id,
                    'sequence': self._get_profitability_sequence_per_invoice_type()[section_id],
                    'billed': amount_invoiced,
                    'to_bill': amount_to_invoice,
                }
                if with_action:
                    bills_costs['action'] = self._get_action_for_profitability_section(list(move_ids), section_id)
                costs['data'].append(bills_costs)
                costs['total']['billed'] += amount_invoiced
                costs['total']['to_bill'] += amount_to_invoice

    def _get_action_for_profitability_section(self, record_ids, name):
        self.ensure_one()
        args = [name, [('id', 'in', record_ids)]]
        if len(record_ids) == 1:
            args.append(record_ids[0])
        return {'name': 'action_profitability_items', 'type': 'object', 'args': json.dumps(args)}

    def _get_profitability_labels(self):
        return {
            **super()._get_profitability_labels(),
            'other_purchase_costs': _lt('Vendor Bills'),
            'other_revenues_aal': _lt('Other Revenues'),
            'other_costs_aal': _lt('Other Costs'),
        }

    def _get_profitability_sequence_per_invoice_type(self):
        return {
            **super()._get_profitability_sequence_per_invoice_type(),
            'other_purchase_costs': 11,
            'other_revenues_aal': 14,
            'other_costs_aal': 15,
        }

    def action_profitability_items(self, section_name, domain=None, res_id=False):
        if section_name in ['other_revenues_aal', 'other_costs_aal']:
            action = self.env["ir.actions.actions"]._for_xml_id("analytic.account_analytic_line_action_entries")
            action['domain'] = domain
            action['context'] = {
                'group_by_date': True,
            }
            if res_id:
                action['views'] = [(False, 'form')]
                action['view_mode'] = 'form'
                action['res_id'] = res_id
            else:
                pivot_view_id = self.env['ir.model.data']._xmlid_to_res_id('project_account.project_view_account_analytic_line_pivot')
                graph_view_id = self.env['ir.model.data']._xmlid_to_res_id('project_account.project_view_account_analytic_line_graph')
                action['views'] = [(pivot_view_id, view_type) if view_type == 'pivot' else (graph_view_id, view_type) if view_type == 'graph' else (view_id, view_type)
                                   for (view_id, view_type) in action['views']]
            return action

        if section_name == 'other_purchase_costs':
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
            action['domain'] = domain or []
            if res_id:
                action['views'] = [(False, 'form')]
                action['view_mode'] = 'form'
                action['res_id'] = res_id
            return action

        return super().action_profitability_items(section_name, domain, res_id)

    def _get_domain_aal_with_no_move_line(self):
        """ this method is used in order to overwrite the domain in sale_timesheet module. Since the field 'project_id' is added to the "analytic line" model
        in the hr_timesheet module, we can't add the condition ('project_id', '=', False) here. """
        return [('auto_account_id', '=', self.analytic_account_id.id), ('move_line_id', '=', False), ('category', '!=', 'manufacturing_order')]

    def _get_items_from_aal(self, with_action=True):
        domain = self._get_domain_aal_with_no_move_line()
        aal_other_search = self.env['account.analytic.line'].sudo().search_read(domain, ['id', 'amount', 'currency_id'])
        if not aal_other_search:
            return {
                'revenues': {'data': [], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}},
                'costs': {'data': [], 'total': {'billed': 0.0, 'to_bill': 0.0}},
            }
        # dict of form  { company : {costs : float, revenues: float}}
        dict_amount_per_currency_id = defaultdict(lambda: {'costs': 0.0, 'revenues': 0.0})
        set_currency_ids = {self.currency_id.id}
        cost_ids = []
        revenue_ids = []
        for aal in aal_other_search:
            set_currency_ids.add(aal['currency_id'][0])
            aal_amount = aal['amount']
            if aal_amount < 0.0:
                dict_amount_per_currency_id[aal['currency_id'][0]]['costs'] += aal_amount
                cost_ids.append(aal['id'])
            else:
                dict_amount_per_currency_id[aal['currency_id'][0]]['revenues'] += aal_amount
                revenue_ids.append(aal['id'])

        total_revenues = total_costs = 0.0
        for currency_id, dict_amounts in dict_amount_per_currency_id.items():
            currency = self.env['res.currency'].browse(currency_id).with_prefetch(dict_amount_per_currency_id)
            total_revenues += currency._convert(dict_amounts['revenues'], self.currency_id, self.company_id)
            total_costs += currency._convert(dict_amounts['costs'], self.currency_id, self.company_id)

        # we dont know what part of the numbers has already been billed or not, so we have no choice but to put everything under the billed/invoiced columns.
        # The to bill/to invoice ones will simply remain 0
        profitability_sequence_per_invoice_type = self._get_profitability_sequence_per_invoice_type()
        revenues = {'id': 'other_revenues_aal', 'sequence': profitability_sequence_per_invoice_type['other_revenues_aal'], 'invoiced': total_revenues, 'to_invoice': 0.0}
        costs = {'id': 'other_costs_aal', 'sequence': profitability_sequence_per_invoice_type['other_costs_aal'], 'billed': total_costs, 'to_bill': 0.0}

        if with_action and self.user_has_groups('account.group_account_readonly'):
            costs['action'] = self._get_action_for_profitability_section(cost_ids, 'other_costs_aal')
            revenues['action'] = self._get_action_for_profitability_section(revenue_ids, 'other_revenues_aal')

        return {
            'revenues': {'data': [revenues], 'total': {'invoiced': total_revenues, 'to_invoice': 0.0}},
            'costs': {'data': [costs], 'total': {'billed': total_costs, 'to_bill': 0.0}},
        }
