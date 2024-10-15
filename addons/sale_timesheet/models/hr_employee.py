# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons import hr_timesheet


class HrEmployee(hr_timesheet.HrEmployee):

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        project_company_id = self.env.context.get('create_project_employee_mapping', False)
        if project_company_id:
            result['company_id'] = project_company_id
        return result
