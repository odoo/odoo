# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _lt

class Project(models.Model):
    _inherit = 'project.project'

    contracts_count = fields.Integer('# Contracts', compute='_compute_contracts_count', groups='hr_payroll.group_hr_payroll_user')

    @api.depends('analytic_account_id')
    def _compute_contracts_count(self):
        contracts_data = self.env['hr.contract']._read_group([
            ('analytic_account_id', '!=', False),
            ('analytic_account_id', 'in', self.analytic_account_id.ids)
        ], ['analytic_account_id'], ['__count'])
        mapped_data = {analytic_account.id: count for analytic_account, count in contracts_data}
        for project in self:
            project.contracts_count = mapped_data.get(project.analytic_account_id.id, 0)

    # -------------------------------------------
    # Actions
    # -------------------------------------------

    def action_open_project_contracts(self):
        contracts = self.env['hr.contract'].search([('analytic_account_id', '!=', False), ('analytic_account_id', 'in', self.analytic_account_id.ids)])
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll.action_hr_contract_repository")
        action.update({
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'context': {'default_analytic_account_id': self.analytic_account_id.id},
            'domain': [('id', 'in', contracts.ids)]
        })
        if(len(contracts) == 1):
            action["views"] = [[False, 'form']]
            action["res_id"] = contracts.id
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super(Project, self)._get_stat_buttons()
        if self.user_has_groups('hr_payroll.group_hr_payroll_user'):
            buttons.append({
                'icon': 'book',
                'text': _lt('Contracts'),
                'number': self.sudo().contracts_count,
                'action_type': 'object',
                'action': 'action_open_project_contracts',
                'show': self.sudo().contracts_count > 0,
                'sequence': 57,
            })
        return buttons
