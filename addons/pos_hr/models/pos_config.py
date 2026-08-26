# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.fields import Domain


class PosConfig(models.Model):
    _name = 'pos.config'
    _inherit = ['hr.mixin', 'pos.config']

    supervised_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_supervised_employee_hr_employee', string="Employees with supervised level access",
        bypass_search_access=True,
        help='Can process sales, but a higher level must approve before payment is closed')
    restrictive_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_restrictive_employee_hr_employee', string="Employees with restrictive level access",
        bypass_search_access=True,
        help='Can process sales and close payments, but not apply discounts, refunds, or cancel orders.')
    cashier_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_cashier_employee_hr_employee', string="Employees with cashier level access",
        bypass_search_access=True,
        help='Full register access. Can process sales, discounts, refunds, and close out payments.')
    manager_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_manager_employee_hr_employee', string="Employees with manager level access",
        bypass_search_access=True,
        help='Full access, including reporting, cash management, and session close.')
    logged_employee_ids = fields.Many2many(
        'hr.employee',
        related='current_session_id.logged_employee_ids',
        readonly=True,
        help="All employees who have logged into the current session",
    )

    def write(self, vals):
        sudo_fields = ('restrictive_employee_ids', 'cashier_employee_ids', 'manager_employee_ids', 'supervised_employee_ids')
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

    def _remove_employee_from_fields(self, employee, field_list):
        for field in field_list:
            if employee in self[field]:
                self[field] -= employee
                break

    @api.onchange('supervised_employee_ids')
    def _onchange_supervised_employee_ids(self):
        role_fields = [
            'cashier_employee_ids',
            'manager_employee_ids',
            'restrictive_employee_ids',
        ]
        for employee in self.supervised_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.supervised_employee_ids -= employee
            else:
                self._remove_employee_from_fields(employee, role_fields)

    @api.onchange('restrictive_employee_ids')
    def _onchange_restrictive_employee_ids(self):
        role_fields = [
            'cashier_employee_ids',
            'manager_employee_ids',
            'supervised_employee_ids',
        ]
        for employee in self.restrictive_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.restrictive_employee_ids -= employee
            else:
                self._remove_employee_from_fields(employee, role_fields)

    @api.onchange('cashier_employee_ids')
    def _onchange_cashier_employee_ids(self):
        role_fields = [
            'manager_employee_ids',
            'restrictive_employee_ids',
            'supervised_employee_ids',
        ]
        for employee in self.cashier_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.cashier_employee_ids -= employee
            else:
                self._remove_employee_from_fields(employee, role_fields)

    @api.onchange('manager_employee_ids')
    def _onchange_manager_employee_ids(self):
        role_fields = [
            'cashier_employee_ids',
            'restrictive_employee_ids',
            'supervised_employee_ids',
        ]
        for employee in self.manager_employee_ids:
            self._remove_employee_from_fields(employee, role_fields)

    def _employee_domain(self, user_id):
        domain = self._check_company_domain(self.company_id)
        domain = Domain.AND([
            domain,
            ['|', ('user_id', '=', user_id), ('id', 'in', self.cashier_employee_ids.ids + self.manager_employee_ids.ids + self.restrictive_employee_ids.ids + self.supervised_employee_ids.ids)]
        ])
        return domain
