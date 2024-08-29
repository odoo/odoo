# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import hr

from odoo import api, models


class HrEmployee(models.Model, hr.HrEmployee):

    @api.model
    def default_get(self, fields):
        result = super(HrEmployee, self).default_get(fields)
        project_company_id = self.env.context.get('create_project_employee_mapping', False)
        if project_company_id:
            result['company_id'] = project_company_id
        return result
