from odoo import models, fields, api
import xlsxwriter
from io import BytesIO


class Customer(models.Model):
    _name = 'sale.customer'
    _description = 'Customer Information'

    # Các trường cơ bản
    partner_platform = fields.Char(string="Sàn Liên Kết")
    name = fields.Char(string="Tên Khách")
    date_of_birth = fields.Date(string="Ngày Sinh")
    id_number = fields.Char(string="CMND / Passport", size=20)
    issue_date = fields.Date(string="Ngày cấp")
    issue_place = fields.Char(string="Nơi cấp")
    permanent_address = fields.Text(string="Địa chỉ thường trú")
    contact_address = fields.Text(string="Địa chỉ liên lạc")

    phone = fields.Char(string="Số điện thoại", size=15)
    email = fields.Char(string="Email")

    # Nhân viên đang phụ trách (có thể thay)
    salesperson_id = fields.Many2one(
        'sale.employee',
        string="Nhân viên phụ trách",
        domain=[('role_ids.code', '=', 'sales')],
        groups="ht_crm.group_ht_executive"
    )

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
    ], string="Phân loại khách")

    status = fields.Selection([
        ('new', 'Khách mới'),
        ('consulting', 'Đang tư vấn'),
        ('followup', 'Follow-up'),
        ('paused', 'Tạm dừng'),
        ('transacting', 'Đã tạo giao dịch'),
        ('lost', 'Mất khách'),
    ], default='new')

    # Đánh dấu khách chăm sóc không thành công
    ignore = fields.Boolean(
        string="Chăm sóc không thành",
        default=False,
        store=True,
        groups="base.group_system,ht_crm.group_ht_leader,ht_crm.group_ht_executive"
    )

    # Dự án khách hàng quan tâm
    project_ids = fields.Many2many(
        'estate.project',
        'estate_project_interested_rel',
        'customer_id',
        'project_id',
        string="Dự án quan tâm"
    )

    transaction_ids = fields.One2many(
        'sale.transaction',
        'customer_id',
        string='Giao dịch'
    )
    

    @api.onchange('ignore')
    def _onchange_field_a(self):
        if self.ignore:
            self.previous_salesperson_ids = [(5, 0, 0)]
