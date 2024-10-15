# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import hr_homeworking, calendar


class ResPartner(hr_homeworking.ResPartner, calendar.ResPartner):

    def get_worklocation(self, start_date, end_date):
        employee_id = self.env['hr.employee'].search([
            ('work_contact_id.id', 'in', self.ids),
            ('company_id.id', '=', self.env.company.id)])
        return employee_id._get_worklocation(start_date, end_date)
