from odoo import models, fields, api
import datetime as dt
import random

class Customer(models.Model):
    _name = 'sale.customer'
    _description = 'Customer Information'

    # Liên kết 1:N với bảng SĐT
    phonebook_ids = fields.One2many(
        "sale.phonebook",
        "customer_id",
        string="Phonebook Entries"
    )

    # Sales đang chăm 
    salesperson_id = fields.Many2one(
        'sale.employee', 
        string="Được Chăm Bởi"
    )

    # Danh sách các Sales đã được gán
    previous_salesperson_ids = fields.Many2many(
        'sale.employee',
        string="Từng Được Chăm Bởi",
        groups="sale_phones.group_ht_executive"
    )

    name = fields.Char(string="Tên khách")
    email = fields.Char(string="Email")

    source = fields.Selection([
        ('facebook', 'Facebook'),
        ('zalo', 'Zalo'),
        ('website', 'Website'),
        ('referral', 'Giới thiệu'),
        ('other', 'Khác'),
    ], string="Nguồn khách")

    type = fields.Selection([
        ('individual', 'Cá nhân'),
        ('broker', 'Môi giới'),
        ('investor', 'Nhà đầu tư'),
        ('company', 'Doanh nghiệp'),
    ], string="Loại khách")

    state = fields.Selection([
        ('active', 'Đang sử dụng'),
        ('inactive', 'Không liên hệ'),
        ('blocked', 'Blocked'),
        ('potential', 'Tiềm năng'),
        ('vip', 'Nét'),
    ], default='active')
    
    # Biến đánh dấu khách chăm thất bại
    ignore = fields.Boolean(
        string="Chăm Không Thành",
        default=False,
        store=True,
        groups="sale_phones.group_ht_leader,sale_phones.group_ht_executive"
    )


    # Dự án quan tâm
    project_ids = fields.Many2many(
        'estate.project',
        string="Đang quan tâm"
    )

    # Hàm đảo ngược quá trình phân KH (dùng tạm)
    def reverse(self):
        sales_users = self.env['res.users'].search([
            ('share', '=', False),
            ('active', '=', True)
        ])

        if not sales_users:
            return
        
        # Với mọi record đang được chọn.
        for record in self:
            record.write({'salesperson_id': ""})
            record.write({'previous_salesperson_ids': [(5, 0, 0)]})

    # Hàm phân KH
    def action_distribute_customers(self):
        eligible_users = self.env['sale.employee'].search([
            ('active', '=', True),
            ('role_ids.code', '=', 'sales')
        ])

        today = dt.datetime.today()
        month = today.month
        year = today.year

        kpis = self.env['sale.employee.kpi'].search([
            ('month', '=', month),
            ('year', '=', year),
        ])

        best_sellers = kpis.filtered(lambda r: r.is_best_seller_by_value or r.is_best_seller_by_quantity)
        best_users = best_sellers.mapped('employee_id')

        if not eligible_users:
            raise Exception("No active users found.")

        # Với mọi record đang được chọn.
        for record in self:
            # Dữ liệu rác
            if record.state == 'blocked':
                continue

            # Skip if this customer has no potential.
            if record.ignore:
                continue

            # ❗ Ưu tiên VIP ("Nét")
            if record.state == 'vip' and best_users:
                available_best = best_users.filtered(
                    lambda u: u not in record.previous_salesperson_ids
                )

                if available_best:
                    assigned_user = random.choice(available_best)
                    record.salesperson_id = assigned_user.id
                    record.previous_salesperson_ids = [(4, assigned_user.id)]
                    continue  # ✅ skip logic thường

            # 👇 Logic cũ cho khách thường
            available = eligible_users.filtered(
                lambda u: u not in record.previous_salesperson_ids
            )

            if not available:
                record.ignore = True
                record.salesperson_id = False
                continue
            else:
                record.ignore = False

            assigned_user = random.choice(available)

            record.salesperson_id = assigned_user.id
            record.previous_salesperson_ids = [(4, assigned_user.id)]

    @api.onchange('ignore')
    def _onchange_field_a(self):
        if self.ignore:
            self.previous_salesperson_ids = [(5, 0, 0)]

    phone = fields.Char(compute="_compute_primary_phone", store=True)

    @api.depends('phonebook_ids.is_primary', 'phonebook_ids.phone')
    def _compute_primary_phone(self):
        for rec in self:
            primary = rec.phonebook_ids.filtered(lambda p: p.is_primary)
            rec.phone = primary[0].phone if primary else False
