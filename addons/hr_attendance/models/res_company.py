# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.osv.expression import OR


class ResCompany(models.Model):
    _inherit = 'res.company'

    hr_attendance_overtime = fields.Boolean(string="Count Extra Hours")
    overtime_start_date = fields.Date(string="Extra Hours Starting Date")

    def write(self, vals):
        search_domain = False
        delete_domain = False

        overtime_enabled = self.filtered('hr_attendance_overtime')
        if 'hr_attendance_overtime' in vals and not vals['hr_attendance_overtime'] and overtime_enabled:
            delete_domain = [('company_id', 'in', overtime_enabled.ids)]
            vals['overtime_start_date'] = False

        start_date = vals.get('hr_attendance_overtime') and 'overtime_start_date' in vals and vals['overtime_start_date']
        if start_date:
            for company in self:
                if not company.overtime_start_date:
                    search_domain = OR([search_domain, [('employee_id.company_id', '=', company.id), ('check_in', '>=', start_date)]])
                elif company.overtime_start_date > start_date:
                    search_domain = OR([search_domain, [('employee_id.company_id', '=', company.id), ('check_in', '>=', start_date), ('check_in', '<=', company.overtime_start_date)]])
                elif company.overtime_start_date < start_date:
                    delete_domain = OR([delete_domain, [('company_id', '=', company.id), ('date', '<', start_date)]])

        res = super().write(vals)
        if delete_domain:
            self.env['hr.attendance.overtime'].search(delete_domain).unlink()
        if search_domain:
            self.env['hr.attendance'].search(search_domain)._update_overtime()

        return res
