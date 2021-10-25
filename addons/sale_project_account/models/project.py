# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _

class Project(models.Model):
    _inherit = 'project.project'

    vendor_bill_count = fields.Integer(related='analytic_account_id.vendor_bill_count', groups='account.group_account_readonly')

    # ----------------------------
    # Actions
    # ----------------------------

    def action_open_project_vendor_bills(self):
        vendor_bills = self.env['account.move'].search([('line_ids.analytic_account_id', '!=', False), ('line_ids.analytic_account_id', 'in', self.analytic_account_id.ids), ('move_type', '=', 'in_invoice')])
        action_window = {
            'name': _('Vendor Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', vendor_bills.ids)],
            'context': {
                'create': False,
            }
        }
        if len(vendor_bills) == 1:
            action_window['views'] = [[False, 'form']]
            action_window['res_id'] = vendor_bills.id
        return action_window

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        if self.user_has_groups('account.group_account_readonly'):
            buttons.append({
                'icon': 'pencil-square-o',
                'text': _('Vendor Bills'),
                'number': self.vendor_bill_count,
                'action_type': 'object',
                'action': 'action_open_project_vendor_bills',
                'show': self.vendor_bill_count > 0,
                'sequence': 14,
            })
        return buttons
