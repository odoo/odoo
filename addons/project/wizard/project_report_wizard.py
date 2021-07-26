# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectReportWizard(models.TransientModel):
    _name = 'project.report.wizard'
    _description = 'Project Report Wizard'

    project_id = fields.Many2one('project.project', required=True)
    report_type = fields.Selection([
        ('burndown', 'Burndown Chart'), ('project_update', 'Project Update')
    ], string='Report Type', required=True, default='burndown')

    def action_burndown_report_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('project.action_project_task_burndown_chart_report')
        action['context'] = {'search_default_project_id': self.project_id.id}
        return action

    def action_project_update_report_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('project.project_update_all_action')
        action['context'] = {'active_id': self.project_id.id, 'search_default_project_id': self.project_id.id}
        return action
