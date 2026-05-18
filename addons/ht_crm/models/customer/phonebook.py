from odoo import models, fields, api, exceptions
import datetime
import random

class PhonebookBatch(models.Model):
    _name = 'sale.phonebook.batch'
    _description = 'Tập dữ liệu Phonebook'

    phonebook_id = fields.One2many(
        'sale.phonebook',
        'group_id',
        string="SĐT thuộc tập",
        domain=[('status', '!=', 'invalid')]
    )
    name = fields.Char(required=True)
    group_key_date = fields.Date(string="Ngày tạo", default=fields.Date.today, groups="ht_crm.group_ht_executive")
    code = fields.Char()

    # Trường bổ sung
    project_id = fields.Many2one('estate.project', required=True, ondelete='cascade')
    sales_ids = fields.Many2many(
        'sale.employee',
        string="Sales trong tập",
    )

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            self.write({'sales_ids': [(6, 0, self.project_id.sales_ids.ids)]})
        else:
            self.write({'sales_ids': [(5, 0, 0)]})

    @api.constrains('sales_ids', 'project_id')
    def _check_sales_in_project(self):
        for rec in self:
            if rec.sales_ids and rec.project_id:
                if not rec.project_id.sales_ids:
                    rec.write({
                        'sales_ids': [(5, 0, 0)]
                    })
                    return

                invalid = rec.sales_ids - rec.project_id.sales_ids
                if invalid:
                    raise exceptions.ValidationError(
                        "Sales phải thuộc project!"
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('project_id') and not vals.get('sales_ids'):
                project = self.env['estate.project'].browse(vals['project_id'])

                vals['sales_ids'] = [(6, 0, project.sales_ids.ids)]

        return super().create(vals_list)
    
    def write(self, vals):
        res = super().write(vals)

        if vals.get('project_id'):
            for rec in self:
                project = rec.project_id

                # chỉ update nếu sales_ids chưa bị user override
                rec.sales_ids = [(6, 0, project.sales_ids.ids)]

        return res

class PhoneBook(models.Model):
    _name = 'sale.phonebook'
    _description = 'DATA danh bạ'

    # Định danh
    group_id = fields.Many2one(
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
    hot_until = fields.Datetime(string="Hết hạn lúc", compute='_compute_hot_until', store=True)
    hot_duration = fields.Integer(
        string="Thời hạn (phút)",
        default=2
    )

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

        now = fields.Datetime.now()

        for rec in self:

            # Khi bật HOT
            if vals.get('is_hot') and not rec.is_hot:

                duration = vals.get('hot_duration') or rec.hot_duration or 0

                vals['hot_until'] = now + datetime.timedelta(minutes=duration)

            # Khi tắt HOT
            if 'is_hot' in vals and not vals['is_hot']:
                vals['hot_until'] = False

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

    @api.depends("hot_duration")
    def _compute_hot_until(self):
        now = fields.Datetime.now()

        for rec in self:
            if not rec.hot_duration:
                rec.hot_until = False
                continue

            rec.hot_until = now + datetime.timedelta(
                minutes=rec.hot_duration
            )

    def get_user_count(self, user_id):
        return self.search_count([
            ('salesperson_id', '=', user_id)
        ])

    def get_available_users(self):
        users = self.env['sale.employee'].search([])

        available = []

        for u in users:
            count = self.search_count([
                ('salesperson_id', '=', u.id)
            ])

            if count < 5:
                available.append(u)

        return available

    @api.model
    def cron_distribute(self):
        now = fields.Datetime.now()

        # Data quảng cáo
        expired = self.search([
            ("status", "!=", "invalid"),
            ("hot_until", "<=", now)
        ])

        for rec in expired:
            rec.auto_distribute_numbers()

            if rec.hot_duration:
                rec.hot_until = now + datetime.timedelta(
                    minutes=rec.hot_duration
                )

    def auto_distribute_numbers(self):    
        # User phụ trách dự án
        eligible_users = self.project_id.sales_ids

        if not self.hot_duration:
            return

        # loại user đã từng được assign record này
        available = eligible_users.filtered(
            lambda u: u not in self.previous_salesperson_ids
        )

        if not available:
            self.write({'salesperson_id': False})
            self.write({'previous_salesperson_ids': [(5, 0, 0)]})
            return

        # ================================
        # 🔥 FILTER: user chưa full slot (max 5)
        # ================================
        valid_users = available.filtered(
            lambda u: self.get_user_count(u.id) < 5
        )

        if not valid_users:
            return exceptions.ValidationError("user")
            self.write({'salesperson_id': False})
            return

        assigned_user = random.choice(valid_users)

        self.salesperson_id = assigned_user.id
        self.previous_salesperson_ids = [(4, assigned_user.id)]

    # Hàm phân KH (ngẫu nhiên)
    def action_distribute_numbers(self):
        # Với mọi record đang được chọn.
        for record in self:
            if record.status == 'invalid':
                continue

            eligible_users = record.project_id.sales_ids

            if not eligible_users:
                record.write({
                    'salesperson_id': False
                })
                continue

            available = eligible_users.filtered(
                lambda u: u not in record.previous_salesperson_ids
            )

            if not available:
                record.write({'salesperson_id': ""})
                record.write({'previous_salesperson_ids': [(5, 0, 0)]})
                continue

            assigned_user = random.choice(available)

            record.salesperson_id = assigned_user.id
            record.previous_salesperson_ids = [(4, assigned_user.id)]
    

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