from odoo import models, fields, api, exceptions
import datetime as dt

class Employee(models.Model):
    _name = 'sale.employee'
    _description = 'Employee Information'

    # Basic info
    name = fields.Char(string="Họ và Tên", required=True)
    code = fields.Char(string="Mã NV")
    active = fields.Boolean(default=True)
    role_ids = fields.Many2many(
        'sale.employee.role',
        'employee_id',
        'role_id',
        string="Roles"
    )

    # Contact
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    address = fields.Text(string="Address")

    # Work info
    department = fields.Char(string="Department") # Thay đổi sau
    manager_id = fields.Many2one('sale.employee')
    child_ids = fields.One2many('sale.employee', 'manager_id')

    # System / tracking
    user_id = fields.Many2one('res.users', string="User Account")
    note = fields.Text(string="Notes")

    _sql_constraints = [
        ('unique_user', 'unique(user_id)', 'Mỗi User chỉ được gán cho 1 nhân viên!')
    ]

class EmployeeRole(models.Model):
    _name = 'sale.employee.role'
    _description = "Employee Role"
    _order = 'sequence, id'

    name = fields.Char(string="Tên vai trò", required=True)
    code = fields.Char(string="Mã", required=True)
    description = fields.Text(string="Mô tả")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã role phải là duy nhất!')
    ]

class EmployeeKPI(models.Model):
    _name = 'sale.employee.kpi'
    _description = 'Employee KPI'

    employee_id = fields.Many2one('sale.employee', required=True)
    month = fields.Integer(string="Tháng", required=True)
    year = fields.Integer(string="Năm", required=True)
    quarter = fields.Integer(string="Quý", compute='_compute_quarter', store=True)

    total_value = fields.Float()

    total_deals = fields.Integer()

    is_best_seller_by_value = fields.Boolean(
        compute='_compute_best_seller',
        store=False
    )

    is_best_seller_by_quantity = fields.Boolean(
        compute='_compute_best_seller',
        store=False
    )

    # Dẫn xuất QUÝ
    @api.depends('month')
    def _compute_quarter(self):
        for rec in self:
            if rec.month:
                rec.quarter = (rec.month - 1) // 3 + 1
            else:
                rec.quarter = 0

    # Dẫn xuất Best Seller (tháng)
    def _compute_best_seller(self):
        for rec in self:
            # tìm max value trong cùng tháng + năm
            kpis = self.search([
                ('month', '=', rec.month),
                ('year', '=', rec.year),
            ])

            max_value = max(kpis.mapped('total_value'), default=0)
            max_deals = max(kpis.mapped('total_deals'), default=0)

            rec.is_best_seller_by_value = rec.total_value == max_value and max_value > 0
            rec.is_best_seller_by_quantity = rec.total_deals == max_deals and max_deals > 0

    @api.constrains('employee_id', 'month', 'year')
    def _check_unique_kpi(self):
        for rec in self:
            existing = self.search([
                ('employee_id', '=', rec.employee_id.id),
                ('month', '=', rec.month),
                ('year', '=', rec.year),
                ('id', '!=', rec.id)
            ], limit=1)

            if existing:
                raise exceptions.ValidationError(
                    "Mỗi nhân viên chỉ có 1 KPI trong cùng tháng/năm!"
                )