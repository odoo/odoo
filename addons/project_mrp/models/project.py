# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _lt


class Project(models.Model):
    _inherit = "project.project"

    production_count = fields.Integer(related="analytic_account_id.production_count", groups='mrp.group_mrp_user')
    workorder_count = fields.Integer(related="analytic_account_id.workorder_count", groups='mrp.group_mrp_user')
    bom_count = fields.Integer(related="analytic_account_id.bom_count", groups='mrp.group_mrp_user')

    def action_view_mrp_production(self):
        self.ensure_one()
        action = self.analytic_account_id.action_view_mrp_production()
        if self.production_count > 1:
            action["view_mode"] = 'tree,form,kanban,calendar,pivot,graph'
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

    def _get_profitability_items(self):
        profitability_items = super()._get_profitability_items()
        mrp_category = 'manufacturing_order'
        mrp_aal_read_group = self.env['account.analytic.line'].sudo()._read_group(
            [('account_id', 'in', self.analytic_account_id.ids), ('category', '=', mrp_category)],
            ['amount'],
            ['account_id'],
        )
        if mrp_aal_read_group:
            mrp_costs = {
                'id': mrp_category,
                'name': _lt('Manufacturing Orders'),
                'billed': sum([res['amount'] for res in mrp_aal_read_group]),
                'to_bill': 0.0,
            }
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
            }])
        return buttons
