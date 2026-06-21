from odoo import models, fields, api, exceptions

class PhonebookStatusWizard(models.TransientModel):
    _name = 'sale.phonebook.status.wizard'
    _description = 'Đổi trạng thái'

    phonebook_id = fields.Many2one('sale.phonebook', string="Bản ghi gốc", required=True)

    status = fields.Selection([
        ('new', 'Chưa liên hệ'),
        ('callback', 'Gọi lại'),
        ('contacted', 'Đã liên hệ'),
        ('invalid', 'Không hợp lệ / Hủy')
    ], string="Trạng thái", default='new', required=True)
    
    # Bỏ required=True ở đây để tránh bị lỗi khi chọn các trạng thái khác ngoài 'callback'
    schedule_callback = fields.Datetime(string="Hẹn gọi lại") 

    def action_confirm(self):
        self.ensure_one()
        
        # 1. RÀNG BUỘC: Chỉ bắt buộc nhập thời gian gọi lại khi trạng thái là 'callback'
        if self.status == 'callback' and not self.schedule_callback:
            raise exceptions.ValidationError("Vui lòng chọn thời gian hẹn gọi lại!")

        # 2. Xử lý chuẩn bị dữ liệu ghi đè lên bản ghi gốc
        vals = {
            'status': self.status,
            # Nếu không phải trạng thái callback, tự động xóa lịch hẹn cũ (nếu có)
            'schedule_callback': self.schedule_callback if self.status == 'callback' else False
        }

        # 3. Ghi dữ liệu đồng thời bằng write kèm context tránh vòng lặp vô hạn
        # Tránh tuyệt đối việc gán self.phonebook_id.status = self.status riêng lẻ trước đó
        self.phonebook_id.with_context(bypass_wizard=True).write(vals)
        
        # 4. Làm mới (Reload) lại màn hình Kanban để cập nhật hiển thị badge mới
        return {
            'type': 'ir.actions.act_window_close',
        }
    
class PhoneBook(models.Model):
    """
    Model quản lý danh bạ Telesales (sale.phonebook).
    Chịu trách nhiệm lưu trữ thông tin số điện thoại, điều phối phân bổ cho Sales,
    giám sát lịch sử tương tác và chuyển đổi thành khách hàng chính thức.
    """
    _name = 'sale.phonebook'
    _description = 'DATA danh bạ'
    _order = "status"

    # =========================================================================
    # 1. KHAI BÁO CÁC TRƯỜNG DỮ LIỆU (FIELDS)
    # =========================================================================
    
    # Định danh & Phân loại dữ liệu
    batch_id = fields.Many2one('sale.phonebook.batch', string="Tập dữ liệu")
    project_id = fields.Many2one(related='batch_id.project_id', string="Dự án")
    source = fields.Char(string="Nguồn Data")
    
    # Thông tin thuê bao cơ bản
    name = fields.Char(string="Chủ thuê bao")
    phone = fields.Char(string="Số điện thoại", size=15, required=True)
    is_hot = fields.Boolean(string="Nóng?", default=False)
    
    # Ghi chú & Hiển thị rút gọn
    note = fields.Text(string="Ghi chú")
    note_preview = fields.Char(compute="_compute_note_preview", store=False, string="Xem trước ghi chú")
    
    # Phân phối & Quản lý Sales phụ trách
    salesperson_id = fields.Many2one('employee.profile.sales', string="Sales phụ trách")
    previous_salesperson_ids = fields.Many2many('employee.profile.sales', string="Lịch sử phụ trách")
    
    # Trạng thái xử lý dữ liệu
    status = fields.Selection([
        ('new', 'Cần xử lý'),
        ('callback', 'Gọi lại'),
        ('contacted', 'Đã liên hệ'),
        ('invalid', 'Không hợp lệ / Hủy')
    ], string="Trạng thái", default='new', store=True, group_expand='_group_expand_status')

    # Theo dõi dòng thời gian & Tương tác (Interaction Tracking)
    schedule_callback = fields.Datetime(string="Hẹn gọi lại")
    created_on = fields.Datetime(string="Ngày tạo số", default=fields.Datetime.now)
    given_at = fields.Datetime(string="Giao vào lúc")
    last_interaction_at = fields.Datetime(string="Tương tác cuối")
    last_interaction_by = fields.Many2one('employee.profile.sales', string="Người xử lý cuối")
    has_interaction_since_given = fields.Boolean(
        compute='_compute_has_interaction_since_given', 
        store=True, 
        index=True,
        string="Đã tương tác từ lúc giao"
    )

    # =========================================================================
    # 2. CÁC HÀM TÍNH TOÁN & Ràng BUỘC (COMPUTE / CONSTRAINS)
    # =========================================================================
    
    @api.onchange('status')
    def _onchange_status(self):
        for record in self:
            if record.status != 'callback':
                record.schedule_callback = False

    @api.depends('note')
    def _compute_note_preview(self):
        """Tính toán đoạn text ngắn hiển thị trên Tree view của Ghi chú"""
        for rec in self:
            rec.note_preview = rec.note[:30] + '...' if rec.note and len(rec.note) > 30 else rec.note

    @api.depends('given_at', 'salesperson_id', 'last_interaction_at', 'last_interaction_by')
    def _compute_has_interaction_since_given(self):
        """Xác định Sales hiện tại đã có tương tác phát sinh kể từ lúc nhận data chưa"""
        for rec in self:
            rec.has_interaction_since_given = bool(
                rec.given_at
                and rec.last_interaction_at
                and rec.last_interaction_at >= rec.given_at
                and rec.last_interaction_by == rec.salesperson_id
            )

    @api.constrains('phone')
    def _check_phone_unique(self):
        """Ràng buộc chống trùng lặp số điện thoại trên toàn hệ thống danh bạ"""
        for rec in self:
            if not rec.phone:
                continue
            existing = self.search([
                ('id', '!=', rec.id),
                ('phone', '=', rec.phone),
            ], limit=1)
            if existing:
                raise exceptions.ValidationError(
                    f"Số điện thoại đã tồn tại trong dự án: {existing.project_id.name or 'Chưa rõ'}"
                )

    # =========================================================================
    # 3. KANBAN / VIEW UTILITIES
    # =========================================================================
    
    @api.model
    def _group_expand_status(self, statuses, domain):
        """Đảm bảo hiển thị đầy đủ các cột trạng thái trên view Kanban kể cả khi cột trống"""
        return [key for key, val in type(self).status.selection]

    # =========================================================================
    # 4. GHI ĐÈ PHƯƠNG THỨC HỆ THỐNG (CRUD OVERRIDES)
    # =========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Ghi đè hàm tạo mới: Đồng bộ thông tin Nguồn Data từ Tập dữ liệu"""
        for vals in vals_list:
            if vals.get('batch_id') and not vals.get('source'):
                batch = self.env['sale.phonebook.batch'].browse(vals['batch_id'])
                if batch.exists():
                    vals['source'] = batch.name
        return super(PhoneBook, self).create(vals_list)

    def write(self, vals):
        """Ghi đè hàm cập nhật: Kiểm tra phân quyền, đồng bộ nguồn và tracking log tương tác"""
        self._check_write_permission(vals)
        self._check_reclaim(vals)

        if 'status' in vals:
            if vals['status'] != 'callback':
                vals['schedule_callback'] = False

        # Xử lý đồng bộ trường Nguồn dữ liệu (Source) khi cập nhật tập dữ liệu (Batch)
        if 'batch_id' in vals:
            if vals['batch_id']:
                batch = self.env['sale.phonebook.batch'].browse(vals['batch_id'])
                vals['source'] = batch.name if batch.exists() else False

        # Lưu lại trạng thái cũ phục vụ phân tích log tương tác
        old_status = {rec.id: rec.status for rec in self}
        tracked_changed = any(field in vals for field in ['status', 'note'])

        res = super(PhoneBook, self).write(vals)

        if tracked_changed:
            self._update_interaction_tracking(old_status)

        # Chỉ kích hoạt nếu không có cờ tránh lặp 'bypass_wizard' từ Wizard gửi lên
                
        return res

    # =========================================================================
    # 5. PHÂN QUYỀN VÀ KIỂM TRA NỘI BỘ (INTERNAL VALIDATIONS / PERMISSIONS)
    # =========================================================================
    
    def _check_write_permission(self, vals):
        """Ngăn chặn tài khoản thông thường sửa các trường hệ thống không được phép"""
        if self.env.user.has_group('base.group_system') or self.env.user.has_group('ht_crm.group_ht_executive'):
            return

        allowed_fields = [
            'note', 'batch_id', 'status', 'source', 
            'has_interaction_since_given', 'last_interaction_at', 'last_interaction_by', 'schedule_callback'
        ]
        forbidden_fields = [field for field in vals if field not in allowed_fields]
        if forbidden_fields:
            raise exceptions.UserError("Bạn chỉ được phép chỉnh sửa ghi chú và trạng thái xử lý dữ liệu.")

    def _check_reclaim(self, vals):
        """Kiểm tra chặn việc Sales cố tình can thiệp vào các số điện thoại đã bị Admin thu hồi"""
        if not self.env.user.has_group('ht_crm.group_ht_sales_user'):
            return

        person = vals.get('salesperson_id')
        if not person:
            return

        salesperson = self.env['employee.profile.sales'].browse(person)
        if self.env.user != salesperson.user_id:
            raise exceptions.UserError("Dữ liệu này đã bị hệ thống thu hồi, bạn không thể xử lý.")

    def _update_interaction_tracking(self, old_status):
        """Cập nhật vết tương tác cuối cùng và cộng dồn KPI sản lượng xử lý trong ngày cho Sales"""
        now = fields.Datetime.now()
        Log = self.env['employee.sales.log']
        handled_counter = {}

        for rec in self:
            is_interacted = (old_status.get(rec.id) == 'new' and rec.status != 'new')
            update_vals = {
                'last_interaction_at': now,
                'last_interaction_by': rec.salesperson_id.id,
            }

            if is_interacted:
                update_vals['batch_id'] = False  # Rút khỏi batch đợi để tránh phân bổ trùng
                if rec.salesperson_id:
                    emp_id = rec.salesperson_id.id
                    handled_counter[emp_id] = handled_counter.get(emp_id, 0) + 1

            rec.with_context(skip_tracking=True).sudo().write(update_vals)

        # Tiến hành cập nhật số lượng KPI đã xử lý vào bảng Nhật ký năng suất (Log)
        if handled_counter:
            today = fields.Date.today()
            for employee_id, qty in handled_counter.items():
                log = Log.sudo().search([
                    ('sales_id', '=', employee_id),
                    ('date', '=', today)
                ], limit=1)

                if not log:
                    log = Log.sudo().create({
                        'sales_id': employee_id,
                        'date': today,
                    })
                log.sudo().write({'handled': log.handled + qty})

    # =========================================================================
    # 6. HÀNH ĐỘNG NGHIỆP VỤ (ACTIONS / BUTTONS)
    # =========================================================================
    
    def get_phone_count_by_salesperson(self, salesperson):
        """Trả về tổng số lượng data một nhân viên đang nắm giữ"""
        return self.search_count([('salesperson_id', '=', salesperson.id)])

    def action_convert_to_customer(self):
        """Chuyển đổi dữ liệu danh bạ thô thành khách hàng chính thức trong hệ thống CRM"""
        self.ensure_one()

        # 1. Kiểm tra chống trùng số điện thoại bên danh sách Khách hàng chính thức
        existing_customer = self.env['sale.customer'].search([('phone', '=', self.phone)], limit=1)
        if existing_customer:
            raise exceptions.UserError(f"Số điện thoại này đã tồn tại trong danh sách Khách hàng với tên: {existing_customer.name}")

        # 2. Tiến hành khởi tạo Khách hàng mới
        customer_vals = {
            'name': self.name or f"Khách hàng {self.phone}",
            'phone': self.phone,
            'salesperson_id': self.salesperson_id.id if self.salesperson_id else False,
            'status': 'new',
        }
        new_customer = self.env['sale.customer'].create(customer_vals)

        # 3. Đổi trạng thái bên danh bạ để đánh dấu hoàn tất xử lý
        if 'status' in self._fields:
            self.status = 'contacted'
            
        # 4. Điều hướng Client hiển thị ngay màn hình Form của Khách hàng vừa tạo
        return {
            'name': 'Khách hàng mới tạo',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.customer',
            'view_mode': 'form',
            'res_id': new_customer.id,
            'target': 'current',
        }

    def action_open_status_wizard(self):
        """Mở cửa sổ Pop-up (Wizard) hỗ trợ Sales cập nhật nhanh trạng thái cuộc gọi"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Đổi trạng thái',
            'res_model': 'sale.phonebook.status.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_phonebook_id': self.id,
                'default_status': self.status,
            }
        }
