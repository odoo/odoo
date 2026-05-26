from odoo import models, fields, api, exceptions
import datetime
import random

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
        required=True
    )

    received = fields.Integer(default=0)
    handled = fields.Integer(default=0)

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
        string="Nhân viên phụ trách"
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
    rest_time = fields.Integer(
        string="Nghỉ (phút)",
        default=2
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

            if batch.rest_time:
                batch.distribute_at = now + datetime.timedelta(
                    minutes=batch.rest_time
                )

    def validate_salesperson_target(self, salesperson):
        count = self.env['sale.phonebook'].search_count([
            ('salesperson_id', '=', salesperson.id)
        ])

        if count >= salesperson.max_received:
            return True

    def action_redistribute(self):
        self.write({'state': 'processing'})
        available_phones = self.phone_ids
        
        for phone in available_phones:
            phone.write({'salesperson_id': False})
            phone.write({'previous_salesperson_ids': False})

    def action_clean_invalid(self):
        invalid_phones = self.phone_ids.filtered(lambda p: p.status == 'invalid')

        for phone in invalid_phones:
            phone.unlink()

    def action_remove_sales(self):
        available_phones = self.phone_ids
        
        for phone in available_phones:
            phone.write({'salesperson_id': False})

    def action_distribute(self):
        self.ensure_one()
        
        employees = self.e_p_rel_ids.mapped('sales_id')
        phones = self.phone_ids

        if not employees or not phones:
            return

        quota = {emp.id: 0 for emp in employees}

        # Track statistic
        received_counter = {}

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
            if self.validate_salesperson_target(employee):
                continue

            phone.write({'salesperson_id': employee.id})
            phone.write({'previous_salesperson_ids': [(4, employee.id)]})
            quota[employee.id] += 1


            # Lifetime counter
            employee.total_received += 1

            # Statistic counter
            received_counter[employee.id] = (
                received_counter.get(employee.id, 0) + 1
            )
            
            all_blocked = False

        # Update statistic log
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

        if all_blocked:
            self.write({'state': 'done'})

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
        domain=[('role_id.code', '=', 'sales')],
        groups="ht_crm.group_ht_executive, ht_crm.group_ht_general_admin"
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

    def get_phone_count_by_salesperson(self, salesperson):
        return self.env['sale.phonebook'].search_count([
            ('salesperson_id', '=', salesperson.id)
        ])

    def write(self, vals):
        # =========================
        # Permission check
        # =========================
        if (
            not self.env.user.has_group('base.group_system')
            and not self.env.user.has_group('ht_crm.group_ht_executive')
        ):

            allowed_fields = ['note', 'status']

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

        # Track old status
        old_status = {
            rec.id: rec.status
            for rec in self
        }

        res = super().write(vals)

        # =========================
        # Update handled statistic
        # =========================
        handled_status = ['contacted', 'callback']

        if 'status' in vals:

            Log = self.env['employee.sales.log']

            for rec in self:

                old = old_status.get(rec.id)
                new = rec.status

                # Chỉ tính khi chuyển từ status khác
                if (
                    old not in handled_status
                    and new in handled_status
                    and rec.salesperson_id
                ):

                    today = fields.Date.today()

                    log = Log.search([
                        ('sales_id', '=', rec.salesperson_id),
                        ('date', '=', today)
                    ], limit=1)

                    if not log:
                        log = Log.create({
                            'sales_id': rec.salesperson_id,
                            'date': today,
                        })

                    log.handled += 1

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

    # log_ids = fields.One2many(
    #     'sale.phonebook.log',
    #     'phonebook_id',
    #     string="Logs"
    # )

    # def write(self, vals):
    #     for rec in self:
    #         old_status = rec.status

    #         res = super(PhoneBook, rec).write(vals)

    #         # Log when status changed
    #         if 'status' in vals and old_status != vals['status']:
    #             self.env['sale.phonebook.log'].create({
    #                 'phonebook_id': rec.id,
    #                 'old_status': old_status,
    #                 'new_status': vals['status'],
    #                 'note': vals.get('note', ''),
    #             })

    #     return True


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