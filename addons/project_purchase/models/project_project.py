# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models, _, _lt
from odoo.osv import expression

from datetime import date

class Project(models.Model):
    _inherit = "project.project"

    purchase_orders_count = fields.Integer('# Purchase Orders', compute='_compute_purchase_orders_count', groups='purchase.group_purchase_user')

    @api.depends('analytic_account_id')
    def _compute_purchase_orders_count(self):
        if not self.analytic_account_id:
            self.purchase_orders_count = 0
            return
        query = self.env['purchase.order.line']._search([])
        query.add_where('purchase_order_line.analytic_distribution ?| %s', [[str(account_id) for account_id in self.analytic_account_id.ids]])

        query_string, query_param = query.select(
            'jsonb_object_keys(purchase_order_line.analytic_distribution) as account_id',
            'COUNT(DISTINCT(order_id)) as purchase_order_count',
        )
        query_string = f"{query_string} GROUP BY jsonb_object_keys(purchase_order_line.analytic_distribution)"

        self._cr.execute(query_string, query_param)
        data = {int(record.get('account_id')): record.get('purchase_order_count') for record in self._cr.dictfetchall()}
        for project in self:
            project.purchase_orders_count = data.get(project.analytic_account_id.id, 0)

    # ----------------------------
    #  Actions
    # ----------------------------

    def action_open_project_purchase_orders(self):
        query = self.env['purchase.order.line']._search([])
        query.add_where('purchase_order_line.analytic_distribution ? %s', [str(self.analytic_account_id.id)])
        query_string, query_param = query.select('order_id')
        self._cr.execute(query_string, query_param)
        purchase_order_ids = [pol.get('order_id') for pol in self._cr.dictfetchall()]
        action_window = {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('id', 'in', purchase_order_ids)],
            'context': {
                'project_id': self.id,
            }
        }
        if len(purchase_order_ids) == 1:
            action_window['views'] = [[False, 'form']]
            action_window['res_id'] = purchase_order_ids[0]
        return action_window

    def action_profitability_items(self, section_name, domain=None, res_id=False):
        if section_name == 'purchase_order':
            action = {
                'name': _('Purchase Order Items'),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order.line',
                'views': [[False, 'tree'], [False, 'form']],
                'domain': domain,
                'context': {
                    'create': False,
                    'edit': False,
                },
            }
            if res_id:
                action['res_id'] = res_id
                if 'views' in action:
                    action['views'] = [
                        (view_id, view_type)
                        for view_id, view_type in action['views']
                        if view_type == 'form'
                    ] or [False, 'form']
                action['view_mode'] = 'form'
            return action
        return super().action_profitability_items(section_name, domain, res_id)

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        if self.user_has_groups('purchase.group_purchase_user'):
            self_sudo = self.sudo()
            buttons.append({
                'icon': 'credit-card',
                'text': _lt('Purchase Orders'),
                'number': self_sudo.purchase_orders_count,
                'action_type': 'object',
                'action': 'action_open_project_purchase_orders',
                'show': self_sudo.purchase_orders_count > 0,
                'sequence': 36,
            })
        return buttons

    def _get_profitability_aal_domain(self):
        return expression.AND([
            super()._get_profitability_aal_domain(),
            ['|', ('move_line_id', '=', False), ('move_line_id.purchase_line_id', '=', False)],
        ])

    def _add_purchase_items(self, profitability_items, with_action=True):
        return False

    def _get_profitability_labels(self):
        labels = super()._get_profitability_labels()
        labels['purchase_order'] = _lt('Purchase Orders')
        return labels

    def _get_profitability_sequence_per_invoice_type(self):
        sequence_per_invoice_type = super()._get_profitability_sequence_per_invoice_type()
        sequence_per_invoice_type['purchase_order'] = 10
        return sequence_per_invoice_type

    def _get_profitability_items(self, with_action=True):
        profitability_items = super()._get_profitability_items(with_action)
        if self.analytic_account_id:
            query = self.env['purchase.order.line'].sudo()._search([
                ('state', 'in', ['purchase', 'done']),
                '|',
                ('qty_invoiced', '>', 0),
                '|', ('qty_to_invoice', '>', 0), ('product_uom_qty', '>', 0),
            ], order=self.env['purchase.order.line']._order)
            query.add_where('purchase_order_line.analytic_distribution ? %s', [str(self.analytic_account_id.id)])
            query_string, query_param = query.select('"purchase_order_line".id', 'qty_invoiced', 'qty_to_invoice', 'product_uom_qty', 'price_unit', 'purchase_order_line.currency_id', '"purchase_order_line".analytic_distribution')
            self._cr.execute(query_string, query_param)
            purchase_order_line_read = [{
                **pol,
                'invoice_lines': self.env['purchase.order.line'].browse(pol['id']).sudo().invoice_lines,  # One2Many cannot be queried, they are not columns
            } for pol in self._cr.dictfetchall()]
            purchase_order_line_invoice_line_ids = self._get_already_included_profitability_invoice_line_ids()
            with_action = with_action and self.user_has_groups('purchase.group_purchase_user, account.group_account_invoice, account.group_account_readonly')
            if purchase_order_line_read:
                # Get conversion rate from currencies to currency of the current company
                convert_company = self.company_id or self.env.company
                currency_ids = {pol['currency_id'] for pol in purchase_order_line_read + [{'currency_id': self.currency_id.id}]}
                rates = self.env['res.currency'].browse(list(currency_ids))._get_rates(convert_company, date.today())
                conversion_rates = {cid: rates[self.currency_id.id] / rate_from for cid, rate_from in rates.items()}

                amount_invoiced = amount_to_invoice = 0.0
                purchase_order_line_ids = []
                for pol_read in purchase_order_line_read:
                    purchase_order_line_invoice_line_ids.extend(pol_read['invoice_lines'].ids)
                    price_unit = self.currency_id.round(pol_read['price_unit'] * conversion_rates[pol_read['currency_id']])
                    analytic_contribution = pol_read['analytic_distribution'][str(self.analytic_account_id.id)] / 100.
                    amount_invoiced -= price_unit * pol_read['qty_invoiced'] * analytic_contribution if pol_read['qty_invoiced'] > 0 else 0.0
                    if pol_read['qty_to_invoice'] > 0:
                        amount_to_invoice -= price_unit * pol_read['qty_to_invoice'] * analytic_contribution
                    else:
                        amount_to_invoice -= price_unit * (pol_read['product_uom_qty'] - pol_read['qty_invoiced']) * analytic_contribution
                    purchase_order_line_ids.append(pol_read['id'])
                costs = profitability_items['costs']
                section_id = 'purchase_order'
                purchase_order_costs = {'id': section_id, 'sequence': self._get_profitability_sequence_per_invoice_type()[section_id], 'billed': amount_invoiced, 'to_bill': amount_to_invoice}
                if with_action and purchase_order_line_ids:
                    args = [section_id, [('id', 'in', purchase_order_line_ids)]]
                    if len(purchase_order_line_ids) == 1:
                        args.append(purchase_order_line_ids[0])
                    action = {'name': 'action_profitability_items', 'type': 'object', 'args': json.dumps(args)}
                    purchase_order_costs['action'] = action
                costs['data'].append(purchase_order_costs)
                costs['total']['billed'] += amount_invoiced
                costs['total']['to_bill'] += amount_to_invoice
            domain = [
                ('move_id.move_type', 'in', ['in_invoice', 'in_refund']),
                ('parent_state', 'in', ['draft', 'posted']),
                ('price_subtotal', '>', 0),
                ('id', 'not in', purchase_order_line_invoice_line_ids),
            ]
            self._get_costs_items_from_purchase(domain, profitability_items, with_action=with_action)
        return profitability_items
