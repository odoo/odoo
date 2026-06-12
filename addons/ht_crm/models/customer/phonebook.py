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
    project_id = fields.Many2one('estate.project', string="Thuộc dự án")

    phone_ids = fields.One2many(
        "sale.phonebook",
        "batch_id",
        string="Danh sách số"
    )

    e_p_rel_ids = fields.One2many(
        'employee.project.rel',
        'batch_id',
        string="Nhân viên phụ trách"
    )

    # Trường phụ
    chunk_size = fields.Integer(string="Chia tối đa", default=3)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('processing', 'Đang phân'),
        ('done', 'Hoàn tất'),
        ('failed', 'Lỗi')
    ], default='draft', string="")
    distribute_at = fields.Datetime(string="Phân phát lúc", compute='_compute_distribute_at', store=True)
    rest_time = fields.Integer(
        string="Nghỉ (phút)",
        default=2
    )

    hot_live_time = fields.Integer(
        string="Thời gian sống số nóng",
        default=3
    )

    cold_live_time = fields.Integer(
        string="Thời gian sống số nguội",
        default=7
    )

    @api.depends("rest_time")
    def _compute_distribute_at(self):
        now = fields.Datetime.now()

        for rec in self:
            if not rec.rest_time:
                rec.distribute_at = False
                continue

            rec.distribute_at = now + datetime.timedelta(
                minutes=rec.rest_time
            )

    # Cron Jobs
    @api.model
    def cron_distribute(self):
        now = fields.Datetime.now()

        # Data quảng cáo
        batches = self.search([
            ("state", "!=", "draft"),
            ("distribute_at", "<=", now)
        ])

        for batch in batches:
            if batch.state == 'failed':
                continue

            if batch.state == 'done':
                batch.reset_assigned_list()
                continue

            # Pre-distribution
            batch.reset_assigned_list()

            batch.action_distribute()

            # Post-distribution
            if batch.rest_time:
                batch.distribute_at = now + datetime.timedelta(
                    minutes=batch.rest_time
                )

    # Actions
    def action_test_cron(self):
        self.cron_distribute()

    def action_redistribute(self):
        self.write({'state': 'processing'})
        available_phones = self.phone_ids
        
        for phone in available_phones:
            phone.write({'salesperson_id': False})
            phone.write({'previous_salesperson_ids': False})
            phone.write({'given_at': False})

    def action_clean_invalid(self):
        invalid_phones = self.phone_ids.filtered(lambda p: p.status == 'invalid')

        for phone in invalid_phones:
            phone.unlink()
    
    def action_distribute(self):
        employees = self.e_p_rel_ids.mapped('sales_id')

        if not employees:
            return

        # Chỉ lấy phone chưa assign
        phones = self.phone_ids.filtered(
            lambda p: not p.salesperson_id
        )

        if not phones:
            self.state = 'done'
            return

        quota = {
            emp.id: (
                self.get_interacted_phone_count(emp)
                + self.get_holding_phone_count(emp)
            )
            for emp in employees
        }

        received_counter = {}

        phone_ids = phones.ids
        random.shuffle(phone_ids)

        now = fields.Datetime.now()

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
                continue  # tất cả full quota

            employee = random.choice(available_emps)
            if self.validate_salesperson_target(employee):
                continue
        
            
            phone.write({
                'given_at': now,
                'salesperson_id': employee.id,
                'previous_salesperson_ids': [(4, employee.id)],
            })
            quota[employee.id] += 1

            # Lifetime statistic
            employee.total_received += 1

            # Batch statistic
            received_counter[employee.id] = (
                received_counter.get(employee.id, 0) + 1
            )

        if received_counter:
            self.update_sales_log(received_counter)

        if self.is_finish_distribution():
            self.state = 'done'

    def update_sales_log(self, received_counter : dict) -> None:
        today = fields.Date.today()
        Log = self.env['employee.sales.log']

        for employee_id, quantity in received_counter.items():

            log = Log.search([
                ('sales_id', '=', employee_id),
                ('date', '=', today)
            ], limit=1)

            if not log:
                log = Log.create({
                    'sales_id': employee_id,
                    'date': today,
                })

            log.received += quantity

    def validate_salesperson_target(self, salesperson):
        count = self.env['sale.phonebook'].search_count([
            ('salesperson_id', '=', salesperson.id)
        ])

        if count >= salesperson.max_received:
            return True
        return False

    def get_unhandled_phones(self, salesperson):
        handled_phone_ids = self.env[
            'sale.phonebook.log'
        ].search([
            ('salesperson_id', '=', salesperson.id)
        ]).mapped('phone_id.id')

        return self.env['sale.phonebook'].search([
            ('salesperson_id', '=', salesperson.id),
            ('id', 'not in', handled_phone_ids)
        ])
    
    def reset_assigned_list(self):

        now = fields.Datetime.now()

        def is_expired(phone):

            if not phone.given_at:
                return True

            live_time = (
                self.hot_live_time
                if phone.is_hot
                else self.cold_live_time
            )

            expired_time = (
                phone.given_at
                + datetime.timedelta(minutes=live_time)
            )

            return now >= expired_time

        phones = self.phone_ids.filtered(
            lambda p:
                p.salesperson_id
                and not p.has_interaction_since_given
                and is_expired(p)
        )

        if phones:
            phones.write({
                'salesperson_id': False,
                'given_at': False,
            })

    def get_interacted_phone_count(self, salesperson):
        return self.env['sale.phonebook'].search_count([
            ('batch_id', '=', self.id),
            ('salesperson_id', '=', salesperson.id),
            ('has_interaction_since_given', '=', True)
        ])
    
    def get_holding_phone_count(self, salesperson):
        now = fields.Datetime.now()

        phones = self.env['sale.phonebook'].search([
            ('batch_id', '=', self.id),
            ('salesperson_id', '=', salesperson.id),
            ('has_interaction_since_given', '=', False),
            ('given_at', '!=', False),
        ])

        def is_holding(phone):
            live_time = (
                self.hot_live_time
                if phone.is_hot
                else self.cold_live_time
            )

            expired_time = (
                phone.given_at
                + datetime.timedelta(minutes=live_time)
            )

            return now < expired_time

        return len(phones.filtered(is_holding))

    def is_finish_distribution(self):
        phones = self.phone_ids.filtered(
            lambda p:
                len(p.previous_salesperson_ids)
                == len(self.e_p_rel_ids)
        )

        return len(phones) == len(self.phone_ids)
    

class PhoneBook(models.Model):
    _name = 'sale.phonebook'
    _description = 'DATA danh bạ'
    _order = "status"

    # Định danh
    batch_id = fields.Many2one(
        'sale.phonebook.batch',
        string="Tập dữ liệu"
    )

    # Trường cơ bản
    name = fields.Char(string="Chủ thuê bao")
    phone = fields.Char(string="Số điện thoại", size=15, required=True)
    note = fields.Text(string="Ghi chú")
    note_preview = fields.Char(
        compute="_compute_note_preview",
        store=False
    )
    created_on = fields.Datetime(
        string="Ngày tạo số",
        default=fields.Datetime.now
    )
    
    # Trường bổ sung
    project_id = fields.Many2one(related='batch_id.project_id', string="Dự án")

    salesperson_id = fields.Many2one(
        'employee.profile.sales',
        string="Sales phụ trách",
    )

    previous_salesperson_ids = fields.Many2many(
        'employee.profile.sales',
        string="Lịch sử phụ trách"
    )

    status = fields.Selection([
        ('new', 'Cần xử lý'),
        ('callback', 'Gọi lại'),
        ('contacted', 'Đã liên hệ'),
        ('invalid', 'Không hợp lệ / Hủy')
    ], string="Trạng thái", default='new', store=True, group_expand='_group_expand_status')

    # Trường xử lý số nóng.
    is_hot = fields.Boolean(string="Nóng?", default=False)

    # Thời gian
    given_at = fields.Datetime(string="Giao vào lúc")
    has_interaction_since_given = fields.Boolean(
        compute='_compute_has_interaction_since_given',
        store=True,
        index=True
    )

    last_interaction_at = fields.Datetime(
        string="Tương tác cuối"
    )

    last_interaction_by = fields.Many2one(
        'employee.profile.sales',
        string="Người xử lý cuối"
    )

    def get_phone_count_by_salesperson(self, salesperson):
        return self.env['sale.phonebook'].search_count([
            ('salesperson_id', '=', salesperson.id)
        ])

    def action_convert_to_customer(self):
        """Hàm chuyển đổi dữ liệu danh bạ thành khách hàng chính thức"""
        self.ensure_one() # Đảm bảo chỉ xử lý trên 1 bản ghi đơn lẻ

        # 1. Kiểm tra xem số điện thoại này đã tồn tại bên bảng khách hàng chưa (tránh trùng lặp)
        existing_customer = self.env['sale.customer'].search([('phone', '=', self.phone)], limit=1)
        if existing_customer:
            raise exceptions.UserError("Số điện thoại này đã tồn tại trong danh sách Khách hàng với tên: %s" % existing_customer.name)

        # 2. Tạo bản ghi mới bên model sale.customer
        customer_vals = {
            'name': self.name, # Nếu danh bạ chưa có tên, đặt tên mặc định
            'phone': self.phone,
            'salesperson_id': self.salesperson_id.id if self.salesperson_id else False,
            'status': 'new', # Trạng thái mặc định bên bảng khách hàng
        }
        new_customer = self.env['sale.customer'].create(customer_vals)

        # 3. (Tùy chọn) Đổi trạng thái hoặc ghi log lại bên danh bạ sau khi chuyển đổi thành công
        if 'status' in self._fields:
            self.status = 'contacted' # Đánh dấu danh bạ đã liên hệ/xử lý thành công
            
        # 4. Trả về một Window Action để tự động mở màn hình Form của Khách hàng mới tạo
        return {
            'name': 'Khách hàng mới tạo',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.customer',
            'view_mode': 'form',
            'res_id': new_customer.id,
            'target': 'current', # Mở đè vào màn hình hiện tại
        }

    @api.depends(
        'given_at',
        'salesperson_id',
        'last_interaction_at',
        'last_interaction_by'
    )
    def _compute_has_interaction_since_given(self):
        for rec in self:
            rec.has_interaction_since_given = bool(
                rec.given_at
                and rec.last_interaction_at
                and rec.last_interaction_at >= rec.given_at
                and rec.last_interaction_by == rec.salesperson_id
            )

    def _check_write_permission(self, vals):
        if (
            self.env.user.has_group('base.group_system')
            or self.env.user.has_group('ht_crm.group_ht_executive')
        ):
            return

        allowed_fields = [
            'note',
            'batch_id',
            'status',
            'has_interaction_since_given',
            'last_interaction_at',
            'last_interaction_by'
        ]

        forbidden_fields = [
            field for field in vals
            if field not in allowed_fields
        ]

        if forbidden_fields:
            raise exceptions.UserError(
                "Bạn chỉ được sửa ghi chú và trạng thái."
            )

    def _check_reclaim(self, vals):
        if not self.env.user.has_group('ht_crm.group_ht_user'):
            return

        person = vals.get('salesperson_id')

        if not person:
            return

        salesperson = self.env[
            'employee.profile.sales'
        ].browse(person)

        if self.env.user != salesperson.user_id:
            raise exceptions.UserError(
                "Số này đã bị thu hồi."
            )
        
    def _update_interaction_tracking(self, old_status):
        now = fields.Datetime.now()

        Log = self.env['employee.sales.log']
        handled_counter = {}

        for rec in self:

            is_interacted = (
                old_status.get(rec.id) == 'new'
                and rec.status != 'new'
            )

            update_vals = {
                'last_interaction_at': now,
                'last_interaction_by': rec.salesperson_id.id,
            }

            if is_interacted:
                update_vals['batch_id'] = False

                if rec.salesperson_id:
                    emp_id = rec.salesperson_id.id
                    handled_counter[emp_id] = handled_counter.get(emp_id, 0) + 1

            rec.with_context(skip_tracking=True).sudo().write(update_vals)

        # update log handled
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

                log.sudo().write({
                    'handled': log.handled + qty,
                })

    def write(self, vals):
        self._check_write_permission(vals)
        self._check_reclaim(vals)

        old_status = {
            rec.id: rec.status
            for rec in self
        }

        tracked_changed = any(
            field in vals
            for field in ['status', 'note']
        )

        res = super().write(vals)

        if tracked_changed:
            self._update_interaction_tracking(old_status)

        return res

    @api.depends('note')
    def _compute_note_preview(self):
        for rec in self:
            if rec.note:
                rec.note_preview = (
                    rec.note[:30] + '...'
                    if len(rec.note) > 30
                    else rec.note
                )
            else:
                rec.note_preview = False

    def action_open_status_wizard(self):
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

    @api.model
    def _group_expand_status(self, statuses, domain):
        return [key for key, val in type(self).status.selection]

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


class PhonebookStatusWizard(models.TransientModel):
    _name = 'sale.phonebook.status.wizard'
    _description = 'Đổi trạng thái'

    phonebook_id = fields.Many2one('sale.phonebook')

    status = fields.Selection([
        ('new', 'Chưa liên hệ'),
        ('callback', 'Gọi lại'),
        ('contacted', 'Đã liên hệ'),
        ('invalid', 'Không hợp lệ / Hủy')
    ], string="Trạng thái", default='new')

    def action_confirm(self):
        self.phonebook_id.status = self.status
