# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class TaskCustomReport(models.AbstractModel):
    _inherit = 'report.industry_fsm.worksheet_custom'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_values = super()._get_report_values(docids, data)
        worksheet_map = {}
        for task in report_values.get('docs'):
            if task.worksheet_template_id:
                x_model = task.worksheet_template_id.sudo().model_id.model
                worksheet = self.env[x_model].search([('x_project_task_id', '=', task.id)], limit=1, order="create_date DESC")  # take the last one
                worksheet_map[task.id] = worksheet
        report_values.update({'worksheet_map': worksheet_map})
        return report_values
