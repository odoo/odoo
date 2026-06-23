# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.fields import Domain


class PosConfig(models.Model):
    _name = 'pos.config'
    _inherit = ['hr.mixin', 'pos.config']

    restrictive_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_restrictive_employee_hr_employee', string="Employees with restrictive level access",
        bypass_search_access=True,
        help='If left empty, all employees can log in to PoS')
    cashier_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_cashier_employee_hr_employee', string="Employees with cashier level access",
        bypass_search_access=True,
        help='If left empty, all employees can log in to PoS')
    manager_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_manager_employee_hr_employee', string="Employees with manager level access",
        bypass_search_access=True,
        help='Employees linked to users with the PoS Manager role are automatically added to this list')
    logged_employee_ids = fields.Many2many(
        'hr.employee',
        related='current_session_id.logged_employee_ids',
        readonly=True,
        help="All employees who have logged into the current session",
    )

    def write(self, vals):
        sudo_fields = ('restrictive_employee_ids', 'cashier_employee_ids', 'manager_employee_ids')
        res = True

        if 'manager_employee_ids' not in vals:
            vals['manager_employee_ids'] = []
        pos_manager_group = self.sudo()._get_group_pos_manager()
        for config in self:
            config_vals = dict(vals)
            group_users = pos_manager_group.with_company(config.company_id).user_ids.filtered(
                lambda u: config.company_id in u.company_ids
            )
            allowed_employees = group_users.employee_id
            if not allowed_employees and group_users:
                target_user = group_users.with_company(config.company_id).filtered(lambda user: not user.employee_id)[0]
                target_user.action_create_employee()
                allowed_employees = target_user.employee_id

            config_vals['manager_employee_ids'] += [(4, emp.id) for emp in allowed_employees]
            sudo_vals = {
                field_name: config_vals.pop(field_name)
                for field_name in sudo_fields
                if not config.env.su
                if isinstance(config_vals.get(field_name), list)
                if all(isinstance(cmd, (list, tuple)) for cmd in config_vals[field_name])
            }
            res &= super().write(config_vals)
            if sudo_vals:
                super(PosConfig, config.sudo()).write(sudo_vals)
        return res

    @api.onchange('restrictive_employee_ids')
    def _onchange_restrictive_employee_ids(self):
        for employee in self.restrictive_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.restrictive_employee_ids -= employee
            elif employee in self.cashier_employee_ids:
                self.cashier_employee_ids -= employee
            elif employee in self.manager_employee_ids:
                self.manager_employee_ids -= employee

    @api.onchange('cashier_employee_ids')
    def _onchange_cashier_employee_ids(self):
        for employee in self.cashier_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.cashier_employee_ids -= employee
            elif employee in self.manager_employee_ids:
                self.manager_employee_ids -= employee
            elif employee in self.restrictive_employee_ids:
                self.restrictive_employee_ids -= employee

    @api.onchange('manager_employee_ids')
    def _onchange_manager_employee_ids(self):
        for employee in self.manager_employee_ids:
            if employee in self.cashier_employee_ids:
                self.cashier_employee_ids -= employee
            if employee in self.restrictive_employee_ids:
                self.restrictive_employee_ids -= employee

    def _employee_domain(self, user_id):
        domain = self._check_company_domain(self.company_id)
        if len(self.cashier_employee_ids) > 0:
            domain = Domain.AND([
                domain,
                ['|', ('user_id', '=', user_id), ('id', 'in', self.cashier_employee_ids.ids + self.manager_employee_ids.ids + self.restrictive_employee_ids.ids)]
            ])
        return domain
