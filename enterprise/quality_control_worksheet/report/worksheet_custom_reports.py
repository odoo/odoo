# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class QualityCustomReport(models.AbstractModel):
    _inherit = "report.quality_control.quality_worksheet"

    @api.model
    def _get_report_values(self, docids, data=None):
        pdf_data = super()._get_report_values(docids, data)

        worksheet_map = {}
        for check in pdf_data.get('docs'):
            if check.worksheet_template_id:
                x_model = check.worksheet_template_id.model_id.model
                worksheet = self.env[x_model].search([('x_quality_check_id', '=', check.id)], limit=1, order="create_date DESC")  # take the last one
                worksheet_map[check.id] = worksheet

        pdf_data['worksheet_map'] = worksheet_map
        return pdf_data
