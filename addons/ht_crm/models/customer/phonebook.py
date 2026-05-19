from odoo import models, fields, api, exceptions
import datetime
import random

class PhonebookBatch(models.Model):
    _name = "sale.phonebook.batch"
    _description = "Phone Dataset"

    # Trường chính
    name = fields.Char(string="Tên tập", required=True)
    date = fields.Date(string="Ngày tạo", default=fields.Date.today)

    # Trường liên kết
    project_id = fields.Many2one('estate.project')

    phone_ids = fields.One2many(
        "sale.phonebook",
        "batch_id",
        string="Danh sách số"
    )

    e_p_rel_ids = fields.One2many(
        'employee.project.rel',
        'batch_id',
        string="Nhân viên phụ trách",
        domain=[('sales_id.role_ids.code', '=', 'sales')]
    )

    # Trường phụ
    chunk_size = fields.Integer(string="Chia tối đa", default=3)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('processing', 'Đang phân'),
        ('done', 'Hoàn tất'),
        ('failed', 'Lỗi')
    ], default='draft')
    distribute_at = fields.Datetime(string="Phân phát lúc", compute='_compute_distribute_at', store=True)
    rest = fields.Integer(
        string="Nghỉ (phút)",
        default=2
    )

    @api.depends("rest")
    def _compute_distribute_at(self):
        now = fields.Datetime.now()

        for rec in self:
            if not rec.rest:
                rec.distribute_at = False
                continue

            rec.distribute_at = now + datetime.timedelta(
                minutes=rec.rest
            )

    @api.model
    def cron_distribute(self):
        now = fields.Datetime.now()

        # Data quảng cáo
        batches = self.search([
            ("state", "!=", "draft"),
            ("distribute_at", "<=", now)
        ])

        for batch in batches:
            if batch.state in ('failed'):
                return

            if batch.state in ('done'):
                batch.action_clean_invalid()

            batch.action_distribute()

            if batch.rest:
                batch.distribute_at = now + datetime.timedelta(
                    minutes=batch.rest
                )


    def action_clean_invalid(self):
        invalid_phones = self.phone_ids.filtered(lambda p: p.is_hot and p.status == 'invalid')

        for phone in invalid_phones:
            phone.unlink()

    def action_remove_sales(self):
        available_phones = self.phone_ids.filtered(lambda p: p.is_hot)
        
        for phone in available_phones:
            phone.write({'salesperson_id': False})
        

    def action_distribute(self):
        self.ensure_one()
        
        employees = self.e_p_rel_ids.mapped('sales_id')
        phones = self.phone_ids.filtered(lambda p: p.is_hot)

        if not employees or not phones:
            return

        quota = {emp.id: 0 for emp in employees}

        self.action_clean_invalid()
        self.action_remove_sales()

        phone_ids = phones.ids
        random.shuffle(phone_ids)

        all_blocked = True
        for phone in self.env['sale.phonebook'].browse(phone_ids):
            filtered = employees.filtered(
                lambda u: u not in phone.previous_salesperson_ids
            )

            if not filtered:
                continue

            available_emps = [
                e for e in filtered
                if quota[e.id] < self.chunk_size
            ]
            
            if not available_emps:
                break  # tất cả full quota

            employee = random.choice(available_emps)

            phone.write({'salesperson_id': employee.id})
            phone.write({'previous_salesperson_ids': [(4, employee.id)]})
            quota[employee.id] += 1
            
            all_blocked = False

        if all_blocked:
            self.write({'state': 'done'})

class PhoneBook(models.Model):
    _name = 'sale.phonebook'
    _description = 'DATA danh bạ'

    # Định danh
    batch_id = fields.Many2one(
        'sale.phonebook.batch',
        string="Tập dữ liệu",
        groups="ht_crm.group_ht_executive"
    )

    # Trường cơ bản
    name = fields.Char(string="Chủ thuê bao")
    phone = fields.Char(string="Số điện thoại", size=15, required=True)
    note = fields.Text(string="Ghi chú")
    created_on = fields.Datetime(
        string="Ngày tạo số",
        default=fields.Datetime.now
    )
    
    # Trường bổ sung
    project_id = fields.Many2one(related='batch_id.project_id')

    salesperson_id = fields.Many2one(
        'sale.employee',
        string="Sales phụ trách",
        domain=[('role_ids.code', '=', 'sales')]
    )

    previous_salesperson_ids = fields.Many2many(
        'sale.employee',
        string="Lịch sử phụ trách",
        groups="ht_crm.group_ht_executive, ht_crm.group_ht_general_admin"
    )

    status = fields.Selection([
        ('new', 'Chưa liên hệ'),
        ('callback', 'Gọi lại'),
        ('contacted', 'Đã liên hệ'),
        ('invalid', 'Không hợp lệ / Hủy')
    ], string="Trạng thái", default='new', store=True)

    # Trường xử lý số nóng.
    is_hot = fields.Boolean(string="Nóng?", default=False)

    def write(self, vals):
        if not self.env.user.has_group('base.group_system') and not self.env.user.has_group('ht_crm.group_ht_executive'):
            allowed_fields = ['note', 'status']

            forbidden_fields = [
                field for field in vals
                if field not in allowed_fields
            ]

            if forbidden_fields:
                raise exceptions.UserError(
                    "Bạn chỉ được sửa ghi chú và trạng thái."
                )

        return super().write(vals)

    @api.constrains('phone')
    def _check_phone_unique(self):
        for rec in self:
            if not rec.phone:
                continue

            existing = self.search([
                ('id', '!=', rec.id),
                ('phone', '=', rec.phone),
            ], limit=1)

            if existing:
                raise exceptions.ValidationError(
                    f"Số điện thoại đã tồn tại "
                    f"trong dự án: {existing.project_id.name}"
                )

    def action_reset_number(self):
        self.ensure_one()
        self.write({'salesperson_id': ""})
        self.write({'previous_salesperson_ids': [(5, 0, 0)]})


class PhoneBookLog(models.Model):
    _name = "sale.phonebook.log"
    _description = "Log thao tác"
    _order = "create_date desc"

    phonebook_id = fields.Many2one(
        "sale.phonebook",
        required=True,
        ondelete="cascade"
    )

    user_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user
    )

    action = fields.Char(required=True)

    note = fields.Text()