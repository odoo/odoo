from odoo import models, fields, api, exceptions
import datetime

class Employee(models.Model):
    _name = 'employee.profile'
    _description = 'Thông Tin Nhân Viên'

    # =========================
    # Basic info
    # =========================
    name = fields.Char(string="Họ và Tên", required=True)
    code = fields.Char(string="Mã NV", size=5) # HT###
    active = fields.Boolean(default=True) 

    role_id = fields.Many2one(
        'employee.profile.role',
        string="Chức danh"
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
    phone = fields.Char(string="SĐT", size=13)
    email = fields.Char(string="Email")
    address = fields.Text(string="Address")

    # =========================
    # Citizen ID
    # =========================
    identity_number = fields.Char(string="CCCD", size=15)

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

    bank_account = fields.Char(string="Số tài khoản", size=20)

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

    # =========================
    # USER SYNC
    # =========================
    def _sync_sales_record(self):
        Sales = self.env['employee.profile.sales']

        for rec in self:
            role_code = rec.role_id.code if rec.role_id else False

            is_sales = role_code in ('sales', 'sales_manager')

            existing = Sales.search([
                ('employee_id', '=', rec.id)
            ], limit=1)

            # CASE 1: cần có sales record
            if is_sales:
                if not existing:
                    Sales.create({
                        'employee_id': rec.id,
                    })
            else:
                # CASE 2: không còn role sales -> xoá hoặc giữ tùy bạn
                if existing:
                    existing.unlink()

    def action_sync_user(self):
        self.ensure_one()

        if not self.env.user.has_group(
            'ht_crm.group_manage_employee'
        ):
            raise exceptions.ValidationError("Bạn không có quyền đồng bộ")

        Users = self.env['res.users'].sudo()

        if self.user_id:

            self.user_id.write({
                'name': self.name,
                'login': self.email,
                'email': self.email,
            })

        else:
            existed = Users.search([
                    ('login', '=', self.email)
                ], limit=1)

            if existed:
                self.user_id = existed.id
                return
            
            user = Users.create({
                'name': self.name,
                'login': self.email,
                'email': self.email,
            })

            self.user_id = user.id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_sales_record()
        return records
    
    def write(self, vals):
        res = super().write(vals)
        self._sync_sales_record()
        return res

class EmployeeSales(models.Model):
    _name = 'employee.profile.sales'
    _description = 'Thông Tin Sales'
    _rec_name = 'name'

    name = fields.Char(related="employee_id.name" , string="Tên Sales", store=True)

    employee_id = fields.Many2one(
        "employee.profile",
        required=True,
        ondelete="cascade",
        domain=['|', ('role_id.code', '=', 'sales'), ('role_id.code', '=', 'sales_manager')]
    )

    manager_id = fields.Many2one(
        'employee.profile.sales',
        string="Quản lý"
    )

    child_ids = fields.One2many(
        'employee.profile.sales',
        'manager_id',
        string="Nhân viên cấp dưới"
    )

    user_id = fields.Many2one(related="employee_id.user_id", store=True)

    total_received = fields.Integer(string="Tổng Data đã nhận", default=0)
    total_handled = fields.Integer(string="Tổng Data đã gọi", default=0, compute='_compute_handled')
    max_received = fields.Integer(string="Nhận tối đa", default=50)
    current_received = fields.Integer(
        string="Đã nhận",
        compute="_compute_received",
        store=True
    )
    performance = fields.Float(string="Hiệu suất (%)", compute='_compute_performance', store=True)

    group_ids = fields.One2many(
        "employee.project.rel",
        "sales_id",
        groups="ht_crm.group_ht_executive"
    )

    # Actions
    def action_reset_counter(self):
        self.total_received = 0
        self.total_handled = 0   

    @api.model
    def get_views(self, views, options=None):
        """Hàm này chạy mỗi khi trang được load (kể cả khi bấm F5)"""
        res = super().get_views(views, options=options)
        
        # Nếu hệ thống đang gọi giao diện Form
        if 'form' in res['views']:
            # Kiểm tra nếu là Admin/Quản lý thì giữ nguyên hoặc ép Form Admin
            if self.env.user.has_group('ht_crm.group_ht_sales_user'):
                sales_view = self.env.ref('ht_crm.view_employee_profile_sales_form_sales').sudo()
                res['views']['form']['id'] = sales_view.id
                res['views']['form']['arch'] = sales_view.arch
            else:
                generic_view = self.env.ref('ht_crm.view_employee_profile_sales_form').sudo()
                res['views']['form']['id'] = generic_view.id
                res['views']['form']['arch'] = generic_view.arch
                # Nếu là Sales thường, F5 kiểu gì cũng phải ra Form Sales tinh gọn
                    
        return res

    @api.model
    def action_open_my_profile(self):
        """Hàm trả về giao diện Form cá nhân dành riêng cho Sales"""
        employee = self.search([('user_id', '=', self.env.user.id)], limit=1)

        if not employee:
            raise exceptions.UserError(("Tài khoản của bạn chưa được liên kết với Hồ sơ Sales nào!"))

        return {
            'name': 'Thông tin cá nhân',
            'type': 'ir.actions.act_window',
            'res_model': 'employee.profile.sales',
            'view_mode': 'form',
            'res_id': employee.id, 
            # ĐÃ CẬP NHẬT: Trỏ đích danh tới ID của Form Sales vừa tạo ở trên
            'views': [(self.env.ref('ht_crm.view_employee_profile_sales_form_sales').id, 'form')], 
            'target': 'current',
        }

    # Constraints
    @api.constrains('employee_id')
    def _check_unique_employee(self):
        for rec in self:
            existed = self.search([
                ('employee_id', '=', rec.employee_id.id),
                ('id', '!=', rec.id)
            ], limit=1)

            if existed:
                raise exceptions.ValidationError(
                    "Nhân viên đã có hồ sơ sales."
                )

    @api.constrains('manager_id')
    def _check_manager(self):
        for rec in self:
            if rec.manager_id == rec:
                raise exceptions.ValidationError("Không thể tự quản lý chính mình.")

    # =========================================================================
    # CÁC HÀM TÍNH TOÁN (COMPUTE FIELDS)
    # =========================================================================

    @api.depends('group_ids.phone_received')
    def _compute_received(self):
        """
        Tính tổng số lượng số điện thoại đã nhận (phân bổ) cho user/salesperson.
        Tiêu chí: Cộng dồn tất cả các số lượng nhận ('phone_received') từ các nhóm (groups) thuộc về bản ghi này.
        """
        for rec in self:
            rec.current_received = sum(
                rec.group_ids.mapped('phone_received')
            )

    @api.depends(
        'group_ids.batch_id.phone_ids',
        'group_ids.batch_id.phone_ids.salesperson_id',
        'group_ids.batch_id.phone_ids.status'
    )
    def _compute_handled(self):
        """
        Tính tổng số lượng số điện thoại ĐÃ XỬ LÝ bởi nhân viên kinh doanh (Salesperson).
        
        TIÊU CHÍ ĐÁNH GIÁ MỘT SỐ ĐÃ XỬ LÝ (STATUS):
        - 'contacted': Đã liên hệ trực tiếp với khách hàng.
        - 'callback' : Khách hẹn gọi lại sau.
        - 'invalid'  : Số không hợp lệ (Số sai, thuê bao, không có thực...) nhưng sales đã kiểm tra và gắn nhãn.
        
        Ghi chú: Các trạng thái khác (ví dụ: 'new' - mới nhận, 'calling' - đang gọi) sẽ KHÔNG được tính là đã xử lý.
        """
        phone_model = self.env['sale.phonebook']

        for rec in self:
            # Đếm số lượng bản ghi trong danh bạ thỏa mãn đồng thời 2 điều kiện:
            # 1. Thuộc quyền quản lý của nhân viên này (salesperson_id == rec.id)
            # 2. Trạng thái nằm trong nhóm các trạng thái đã hoàn thành xử lý
            rec.total_handled = phone_model.search_count([
                ('salesperson_id', '=', rec.id),
                ('status', 'in', ['contacted', 'callback', 'invalid'])
            ])

    @api.depends('total_received', 'total_handled')
    def _compute_performance(self):
        for rec in self:
            if rec.total_received == 0:
                rec.performance = 0
                continue
            rec.performance = (rec.total_handled / rec.total_received) * 100


class EmployeeRole(models.Model):
    _name = 'employee.profile.role'
    _description = "Thông Tin Chức Danh"
    _order = 'sequence, id'

    name = fields.Char(string="Tên vai trò", required=True)
    code = fields.Char(string="Mã", required=True)
    description = fields.Text(string="Mô tả")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã role phải là duy nhất!')
    ]

class EmployeeSalesLog(models.Model):
    _name = 'employee.sales.log'
    _description = 'Sales Statistic Log'
    _order = 'date desc'

    sales_id = fields.Many2one(
        'employee.profile.sales',
        required=True,
        ondelete='cascade'
    )

    date = fields.Date(
        default=fields.Date.today,
        required=True,
        string="Ngày tạo"
    )

    received = fields.Integer(default=0, string="Đã nhận")
    handled = fields.Integer(default=0, string="Đã xử lý")

    performance = fields.Float(
        compute='_compute_performance',
        store=True
    )

    @api.depends('received', 'handled')
    def _compute_performance(self):
        for rec in self:
            if rec.received:
                rec.performance = (
                    rec.handled / rec.received
                ) * 100
            else:
                rec.performance = 0

class EmployeeKPI(models.Model):
    _name = 'employee.profile.sales.kpi'
    _description = 'Employee KPI'

    employee_id = fields.Many2one('employee.profile.sales', required=True)
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