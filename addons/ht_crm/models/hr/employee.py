from odoo import models, fields, api, exceptions
import datetime

class Employee(models.Model):
    _name = 'sale.employee'
    _description = 'Employee Information'

    # =========================
    # Basic info
    # =========================
    name = fields.Char(string="Họ và Tên", required=True)
    code = fields.Char(string="Mã NV")
    active = fields.Boolean(default=True)

    role_id = fields.Many2one(
        'sale.employee.role',
        string="Chức danh"
    )

    project_ids = fields.One2many(
        'employee.project.rel',
        'sales_id',
        string="Dự án phụ trách"
    )

    # =========================
    # Personal info
    # =========================
    gender = fields.Selection([
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('other', 'Khác'),
    ], string="Giới tính")

    birthday = fields.Date(string="Ngày sinh")

    birth_year = fields.Integer(
        string="Năm sinh",
        compute="_compute_birth_year",
        store=True
    )

    hometown = fields.Char(string="Quê quán")

    permanent_address = fields.Text(string="Địa chỉ thường trú")

    temporary_address = fields.Text(string="Địa chỉ tạm trú")

    # =========================
    # Contact
    # =========================
    phone = fields.Char(string="SĐT")
    email = fields.Char(string="Email")
    address = fields.Text(string="Address")

    # =========================
    # Citizen ID
    # =========================
    identity_number = fields.Char(string="CCCD")

    identity_issue_date = fields.Date(string="Ngày cấp")

    identity_issue_place = fields.Char(string="Nơi cấp")

    # =========================
    # Tax / Insurance
    # =========================
    tax_code = fields.Char(string="Mã số thuế")

    social_insurance_number = fields.Char(string="Mã BHXH")

    # =========================
    # Bank
    # =========================
    bank_name = fields.Char(string="Tên ngân hàng")

    bank_account = fields.Char(string="Số tài khoản")

    bank_branch = fields.Char(string="Chi nhánh")

    # =========================
    # Work info
    # =========================
    department = fields.Char(string="Phòng ban")

    start_work_date = fields.Date(string="Ngày bắt đầu làm việc")

    seniority = fields.Char(
        string="Thâm niên",
        compute="_compute_seniority",
        store=True
    )

    manager_id = fields.Many2one(
        'sale.employee',
        string="Quản lý"
    )

    child_ids = fields.One2many(
        'sale.employee',
        'manager_id',
        string="Nhân viên cấp dưới"
    )

    # =========================
    # System / tracking
    # =========================
    user_id = fields.Many2one(
        'res.users',
        string="Tài khoản đăng nhập"
    )

    note = fields.Text(string="Ghi chú")

    # =========================
    # Constraints
    # =========================
    @api.constrains('user_id')
    def _check_unique_user(self):

        for rec in self:

            if not rec.user_id:
                continue

            duplicate = self.search([
                ('id', '!=', rec.id),
                ('user_id', '=', rec.user_id.id),
            ], limit=1)

            if duplicate:
                raise exceptions.ValidationError(
                    "Mỗi User chỉ được gán cho 1 nhân viên!"
                )

    @api.constrains('code')
    def _check_unique_code(self):
        for rec in self:

            if not rec.code:
                continue

            duplicate = self.search([
                ('id', '!=', rec.id),
                ('code', '=', rec.code),
            ], limit=1)

            if duplicate:
                raise exceptions.ValidationError(
                    "Mã nhân viên đã tồn tại!"
                )

    @api.constrains('identity_number')
    def _check_unique_identity(self):

        for rec in self:

            if not rec.identity_number:
                continue

            duplicate = self.search([
                ('id', '!=', rec.id),
                ('identity_number', '=', rec.identity_number),
            ], limit=1)

            if duplicate:
                raise exceptions.ValidationError(
                    "CCCD đã tồn tại!"
                )

    # =========================
    # Compute
    # =========================
    @api.depends('start_work_date')
    def _compute_seniority(self):
        today = fields.Date.today()

        for rec in self:

            rec.seniority = False

            if rec.start_work_date:

                delta_years = today.year - rec.start_work_date.year
                delta_months = today.month - rec.start_work_date.month

                # Nếu chưa tới ngày trong tháng
                if today.day < rec.start_work_date.day:
                    delta_months -= 1

                # Normalize month
                if delta_months < 0:
                    delta_years -= 1
                    delta_months += 12

                parts = []

                if delta_years > 0:
                    parts.append(f"{delta_years} năm")

                if delta_months > 0:
                    parts.append(f"{delta_months} tháng")

                rec.seniority = " ".join(parts) or "Dưới 1 tháng"
    
    @api.depends('birthday')
    def _compute_birth_year(self):
        for rec in self:
            rec.birth_year = rec.birthday.year if rec.birthday else False

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