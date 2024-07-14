# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class TaskCustomReport(models.AbstractModel):
    _name = 'report.industry_fsm_report.worksheet_custom'
    _description = 'Task Worksheet Custom Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        tasks = self.env['project.task'].browse(docids).sudo()
        worksheet_map = {}
        for task in tasks:
            if task.worksheet_template_id:
                x_model = task.worksheet_template_id.model_id.model
                worksheet = self.env[x_model].search([('x_project_task_id', '=', task.id)], limit=1, order="create_date DESC")  # take the last one
                worksheet_map[task.id] = worksheet
        return {
            'doc_ids': docids,
            'doc_model': 'project.task',
            'docs': tasks,
            'worksheet_map': worksheet_map,
        }
