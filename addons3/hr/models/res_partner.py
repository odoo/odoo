# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class Partner(models.Model):
    _inherit = ['res.partner']

    employee_ids = fields.One2many(
        'hr.employee', 'work_contact_id', string='Employees', groups="hr.group_hr_user",
        help="Related employees based on their private address")
    employees_count = fields.Integer(compute='_compute_employees_count', groups="hr.group_hr_user")

    def _compute_employees_count(self):
        for partner in self:
            partner.employees_count = len(partner.employee_ids.filtered(lambda e: e.company_id in self.env.companies))

    def action_open_employees(self):
        self.ensure_one()
        if self.employees_count > 1:
            return {
                'name': _('Related Employees'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.employee',
                'view_mode': 'kanban',
                'domain': [('id', 'in', self.employee_ids.ids),
                           ('company_id', 'in', self.env.companies.ids)],
            }
        return {
            'name': _('Employee'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_ids.id,
            'view_mode': 'form',
        }

    def _get_all_addr(self):
        self.ensure_one()
        employee_id = self.env['hr.employee'].search(
            [('id', 'in', self.employee_ids.ids)],
            limit=1,
        )
        if not employee_id:
            return super()._get_all_addr()

        pstl_addr = {
            'contact_type': 'employee',
            'street': employee_id.private_street,
            'zip': employee_id.private_zip,
            'city': employee_id.private_city,
            'country': employee_id.private_country_id.code,
        }
        return [pstl_addr] + super()._get_all_addr()
