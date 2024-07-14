# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MaintenanceRequestReport(models.AbstractModel):
    _name = 'report.maintenance_worksheet.maintenance_worksheet'
    _description = 'Maintenance Request Worksheet Custom Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['maintenance.request'].browse(docids).sudo()
        worksheet_map = {}
        for request in docs:
            if request.worksheet_template_id:
                x_model = request.worksheet_template_id.model_id.model
                worksheet = self.env[x_model].search([('x_maintenance_request_id', '=', request.id)])
                worksheet_map[request.id] = worksheet
        return {
            'doc_model': 'maintenance.request',
            'doc_ids': docids,
            'docs': docs,
            'worksheet_map': worksheet_map,
        }
