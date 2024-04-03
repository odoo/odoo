# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _lt
from odoo.osv import expression


class Project(models.Model):
    _inherit = "project.project"

    production_count = fields.Integer(related="analytic_account_id.production_count", groups='mrp.group_mrp_user')
    workorder_count = fields.Integer(related="analytic_account_id.workorder_count", groups='mrp.group_mrp_user')
    bom_count = fields.Integer(related="analytic_account_id.bom_count", groups='mrp.group_mrp_user')

    def action_view_mrp_production(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('mrp.mrp_production_action')
        action['domain'] = [('analytic_account_id', '=', self.analytic_account_id.id)]
        action['context'] = {'default_analytic_account_id': self.analytic_account_id.id}
        if self.production_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.analytic_account_id.production_ids.id
            if 'views' in action:
                action['views'] = [
                    (view_id, view_type)
                    for view_id, view_type in action['views']
                    if view_type == 'form'
                ] or [False, 'form']
        return action

    def action_view_mrp_bom(self):
        self.ensure_one()
        action = self.analytic_account_id.action_view_mrp_bom()
        if self.bom_count > 1:
            action['view_mode'] = 'tree,form,kanban'
        return action

    def action_view_workorder(self):
        self.ensure_one()
        action = self.analytic_account_id.action_view_workorder()
        if self.workorder_count > 1:
            action['view_mode'] = 'tree,form,kanban,calendar,pivot,graph'
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_profitability_labels(self):
        labels = super()._get_profitability_labels()
        labels['manufacturing_order'] = _lt('Manufacturing Orders')
        return labels

    def _get_profitability_sequence_per_invoice_type(self):
        sequence_per_invoice_type = super()._get_profitability_sequence_per_invoice_type()
        sequence_per_invoice_type['manufacturing_order'] = 10
        return sequence_per_invoice_type

    def _get_profitability_aal_domain(self):
        return expression.AND([
            super()._get_profitability_aal_domain(),
            [('category', '!=', 'manufacturing_order')],
        ])

    def _get_profitability_items(self, with_action=True):
        profitability_items = super()._get_profitability_items(with_action)
        mrp_category = 'manufacturing_order'
        mrp_aal_read_group = self.env['account.analytic.line'].sudo()._read_group(
            [('account_id', 'in', self.analytic_account_id.ids), ('category', '=', mrp_category)],
            ['amount'],
            ['account_id'],
        )
        if mrp_aal_read_group:
            can_see_manufactoring_order = with_action and len(self) == 1 and self.user_has_groups('mrp.group_mrp_user')
            mrp_costs = {
                'id': mrp_category,
                'sequence': self._get_profitability_sequence_per_invoice_type()[mrp_category],
                'billed': sum([res['amount'] for res in mrp_aal_read_group]),
                'to_bill': 0.0,
            }
            if can_see_manufactoring_order:
                mrp_costs['action'] = {'name': 'action_view_mrp_production', 'type': 'object'}
            costs = profitability_items['costs']
            costs['data'].append(mrp_costs)
            costs['total']['billed'] += mrp_costs['billed']
        return profitability_items

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        if self.user_has_groups('mrp.group_mrp_user'):
            buttons.extend([{
                'icon': 'flask',
                'text': _lt('Bills of Materials'),
                'number': self.bom_count,
                'action_type': 'object',
                'action': 'action_view_mrp_bom',
                'show': self.bom_count > 0,
                'sequence': 45,
            },
            {
                'icon': 'wrench',
                'text': _lt('Manufacturing Orders'),
                'number': self.production_count,
                'action_type': 'object',
                'action': 'action_view_mrp_production',
                'show': self.production_count > 0,
                'sequence': 46,
            }])
        return buttons
