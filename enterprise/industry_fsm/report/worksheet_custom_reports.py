# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, models


class TaskCustomReport(models.AbstractModel):
    _name = 'report.industry_fsm.worksheet_custom'
    _description = 'Task Worksheet Custom Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['project.task'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'project.task',
            'docs': docs,
        }
