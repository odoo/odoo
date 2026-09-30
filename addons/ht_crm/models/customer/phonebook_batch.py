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
    
    def action_notify(self, message):
        # 1. Định nghĩa nội dung tin nhắn của Bot
        message_body = message
        
        # 2. Tìm kênh 'General' (Kênh chung mặc định của Odoo)
        channel = self.env['discuss.channel'].search([('name', '=', 'sales')], limit=1)
        
        if channel:
            # 3. Lấy ID của OdooBot (System Root User)
            odoobot_id = self.env.ref('base.user_root').id
            
            # 4. Ép quyền gửi dưới danh nghĩa OdooBot
            channel.with_user(odoobot_id).message_post(
                body=message_body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment'
            )
        else:
            # Trường hợp không tìm thấy kênh General, báo lỗi nhẹ để biết
            raise exceptions.UserError("Không tìm thấy kênh mang tên 'general' trong Discuss.")

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