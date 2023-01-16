# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, _lt


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

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        if self.user_has_groups('mrp.group_mrp_user'):
            buttons.extend([{
                'icon': 'wrench',
                'text': _lt('Manufacturing Orders'),
                'number': self.production_count,
                'action_type': 'object',
                'action': 'action_view_mrp_production',
                'show': self.production_count > 0,
                'sequence': 19,
            },
            {
                'icon': 'cog',
                'text': _lt('Work Orders'),
                'number': self.workorder_count,
                'action_type': 'object',
                'action': 'action_view_workorder',
                'show': self.workorder_count > 0,
                'sequence': 20,
            },
            {
                'icon': 'flask',
                'text': _lt('Bills of Materials'),
                'number': self.bom_count,
                'action_type': 'object',
                'action': 'action_view_mrp_bom',
                'show': self.bom_count > 0,
                'sequence': 21,
            }])
        return buttons
