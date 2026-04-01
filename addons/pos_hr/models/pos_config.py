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
        sudo_vals = {}
        for field_name in ('minimal_employee_ids', 'basic_employee_ids', 'advanced_employee_ids'):
            if self.env.su:
                continue
            value = vals.get(field_name)
            if isinstance(value, list) and all(isinstance(cmd, (list, tuple)) for cmd in value):
                sudo_vals[field_name] = vals.pop(field_name)

        res = True
        for company in self.mapped('company_id'):
            company_records = self.filtered(lambda r: r.company_id == company)
            company_vals = dict(vals)
            advanced_employees = list(company_vals.get('advanced_employee_ids') or [])

            group_users = company_records.sudo()._get_group_pos_manager().user_ids.filtered(
                lambda u: company in u.company_ids
            )
            allowed_employees = group_users.sudo().mapped('employee_id')
            if not allowed_employees and group_users:
                users_without_employee = group_users.with_company(company).filtered(lambda u: not u.employee_id)
                if users_without_employee:
                    target_user = users_without_employee[0]
                    target_user.action_create_employee()
                    allowed_employees = target_user.employee_id

            advanced_employees += [(4, emp.id) for emp in allowed_employees]
            company_vals['advanced_employee_ids'] = advanced_employees
            res = super(PosConfig, company_records).write(company_vals) and res
            if sudo_vals:
                super(PosConfig, company_records.sudo()).write(sudo_vals)

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
