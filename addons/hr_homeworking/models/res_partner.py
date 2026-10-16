# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_im_status(self):
        super()._compute_im_status()
        # sudo: hr.employee - can read the location of users, exceptions included, to show IM status
        employee_by_user = self.user_ids.sudo()._get_employee_by_user()
        for user in self.user_ids:
            dayfield = self.env['hr.employee']._get_current_day_location_field()
            employee = employee_by_user[user]
            location_type = (employee.exceptional_location_id or employee[dayfield]).location_type
            if not location_type:
                continue
            im_status = user.partner_id.im_status
            if im_status == "online" or im_status == "away" or im_status == "offline":
                user.partner_id.im_status = location_type + "_" + im_status

    def get_worklocation(self, start_date, end_date):
        employee_id = self.env['hr.employee'].search([
            ('work_contact_id', 'in', self.ids),
            ('company_id', '=', self.env.company.id)])
        return employee_id._get_worklocation(start_date, end_date)
