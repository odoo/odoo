# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class MultiEmployeeSalesReport(models.AbstractModel):
    _name = 'report.pos_hr.multi_employee_sales_report'
    _description = 'A collection of single session reports. One for each employee'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        data.update({
            'session_ids': data.get('session_ids'),
            'employee_ids': data.get('employee_ids'),
            'config_ids': data.get('config_ids'),
            'date_start': data.get('date_start'),
            'date_stop': data.get('date_stop'),
        })
        return data
