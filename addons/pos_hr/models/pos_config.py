# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.fields import Domain


class PosConfig(models.Model):
    _name = 'pos.config'
    _inherit = ['hr.mixin', 'pos.config']

    minimal_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_minimal_employee_hr_employee', string="Employees with minimal access",
        help='If left empty, all employees can log in to PoS')
    basic_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_basic_employee_hr_employee', string="Employees with basic access",
        help='If left empty, all employees can log in to PoS')
    advanced_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_advanced_employee_hr_employee', string="Employees with manager access",
        help='Employees linked to users with the PoS Manager role are automatically added to this list')

    def write(self, vals):
        if 'advanced_employee_ids' not in vals:
            vals['advanced_employee_ids'] = []
        vals['advanced_employee_ids'] += [(4, emp_id) for emp_id in self._get_group_pos_manager().user_ids.employee_id.ids]

        # write employees in sudo, because we have no access to these corecords
        sudo_vals = {
            field_name: value
            for field_name in ('minimal_employee_ids', 'basic_employee_ids', 'advanced_employee_ids')
            if not self.env.su
            if (value := vals.pop(field_name, ()))
        }

        res = super().write(vals)
        if sudo_vals:
            super(PosConfig, self.sudo()).write(sudo_vals)
        return res

    @api.onchange('minimal_employee_ids')
    def _onchange_minimal_employee_ids(self):
        for employee in self.minimal_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.minimal_employee_ids -= employee
            elif employee in self.basic_employee_ids:
                self.basic_employee_ids -= employee
            elif employee in self.advanced_employee_ids:
                self.advanced_employee_ids -= employee

    @api.onchange('basic_employee_ids')
    def _onchange_basic_employee_ids(self):
        for employee in self.basic_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.basic_employee_ids -= employee
            elif employee in self.advanced_employee_ids:
                self.advanced_employee_ids -= employee
            elif employee in self.minimal_employee_ids:
                self.minimal_employee_ids -= employee

    @api.onchange('advanced_employee_ids')
    def _onchange_advanced_employee_ids(self):
        for employee in self.advanced_employee_ids:
            if employee in self.basic_employee_ids:
                self.basic_employee_ids -= employee
            if employee in self.minimal_employee_ids:
                self.minimal_employee_ids -= employee

    def _employee_domain(self, user_id):
        domain = self._check_company_domain(self.company_id)
        if len(self.basic_employee_ids) > 0:
            domain = Domain.AND([
                domain,
                ['|', ('user_id', '=', user_id), ('id', 'in', self.basic_employee_ids.ids + self.advanced_employee_ids.ids + self.minimal_employee_ids.ids)]
            ])
        return domain
