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
            ("state", "!=", "draft")
        ])

        for batch in batches:
            if batch.state == 'failed':
                continue

            if batch.state == 'done':
                continue

            # Pre-distribution
            self.reset_assigned_list()

            batch.action_distribute()

            # Post-distribution
            if batch.rest_time:
                batch.distribute_at = now + datetime.timedelta(
                    minutes=batch.rest_time
                )

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

    def reset_assigned_list(self):
        # Nếu đã tương tác -> Bỏ ra khỏi danh sách
        phones = self.phone_ids.filtered(
            lambda p: p.salesperson_id and not p.has_interaction_since_given
        )
        for phone in phones:
            phone.write({
                'salesperson_id': False,
                'given_at': False,
            })

    def get_active_phone_count(self, salesperson):
        return self.env['sale.phonebook'].search_count([
            ('batch_id', '=', self.id),
            ('salesperson_id', '=', salesperson.id),
            ('has_interaction_since_given', '=', True)
        ])

    # Cron 1: Distributor
    def action_distribute(self):
        def can_reassign(phone):
            if not phone.given_at:
                return True

            live_time = (
                self.hot_live_time
                if phone.is_hot
                else self.cold_live_time
            )

            expired_time = phone.given_at + datetime.timedelta(minutes=live_time)

            if now >= expired_time:
                return False
        
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
            emp.id: self.get_active_phone_count(emp)
            for emp in employees
        }

        received_counter = {}

        phone_ids = phones.ids
        random.shuffle(phone_ids)

        has_assignment = False

        now = fields.Datetime.now()

        for phone in self.env[
            'sale.phonebook'
        ].browse(phone_ids):

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
            if self.validate_salesperson_target(employee):
                continue
            
            # Check thời gian sống
            if not can_reassign(phone):
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

            has_assignment = True

        if received_counter:
            self.update_sales_log(received_counter)

        # Không còn số nào để assign
        if not has_assignment:
            self.state = 'done'

class PhoneBook(models.Model):
    _name = 'sale.phonebook'
    _description = 'DATA danh bạ'
    _order = "status"

    # Định danh
    batch_id = fields.Many2one(
        'sale.phonebook.batch',
        string="Tập dữ liệu",
        groups="ht_crm.group_manage_phone_data"
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
        string="Lịch sử phụ trách",
        groups="ht_crm.group_ht_executive, ht_crm.group_ht_general_admin"
    )

    status = fields.Selection([
        ('new', 'Chưa liên hệ'),
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
    
    def validate_fields_access():
        pass

    def write(self, vals):
        # =========================
        # Permission check
        # =========================
        if (
            not self.env.user.has_group('base.group_system')
            and not self.env.user.has_group('ht_crm.group_ht_executive')
        ):

            allowed_fields = ['note', 'batch_id' , 'status', 'has_interaction_since_given', 'last_interaction_at', 'last_interaction_by']

            forbidden_fields = [
                field for field in vals
                if field not in allowed_fields
            ]

            if forbidden_fields:
                raise exceptions.UserError(
                    "Bạn chỉ được sửa ghi chú và trạng thái."
                )

        # =========================
        # Check reclaim
        # =========================
        if self.env.user.has_group('ht_crm.group_ht_user'):

            person = vals.get('salesperson_id')

            if person:

                salesperson = self.env[
                    'employee.profile.sales'
                ].browse(person)

                if self.env.user != salesperson.user_id:
                    raise exceptions.UserError(
                        "Số này đã bị thu hồi."
                    )

        # =========================
        # Xử lý số
        # =========================
        tracked_changed = any(
            field in vals
            for field in ['status', 'note']
        )

        old_status = {
            rec.id: rec.status
            for rec in self
        }

        res = super().write(vals)

        if tracked_changed:

            now = fields.Datetime.now()

            for rec in self:

                update_vals = {
                    'last_interaction_at': now,
                    'last_interaction_by': rec.salesperson_id.id,
                }

                # Nếu từ new -> status khác
                if (
                    old_status.get(rec.id) == 'new'
                    and rec.status != 'new'
                ):
                    update_vals.update({
                        'batch_id': False
                    })

                rec.sudo().update(update_vals)

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

    def action_reset_number(self):
        self.ensure_one()
        self.write({'salesperson_id': ""})
        self.write({'previous_salesperson_ids': [(5, 0, 0)]})


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
