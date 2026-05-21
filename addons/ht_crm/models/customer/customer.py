from odoo import models, fields, api
import xlsxwriter
from io import BytesIO


class Customer(models.Model):
    _name = 'sale.customer'
    _description = 'Customer Information'

    # Các trường cơ bản
    partner_platform = fields.Char(string="Sàn Liên Kết")
    name = fields.Char(string="Tên khách hàng", required=True)
    date_of_birth = fields.Date(string="Ngày sinh")
    id_number = fields.Char(string="CMND / Passport", size=20)
    issue_date = fields.Date(string="Ngày cấp")
    issue_place = fields.Char(string="Nơi cấp")
    permanent_address = fields.Text(string="Địa chỉ thường trú")
    contact_address = fields.Text(string="Địa chỉ liên lạc")

    phone = fields.Char(string="Số điện thoại", size=15, required=True)
    email = fields.Char(string="Email")

    # Nhân viên đang phụ trách (có thể thay)
    salesperson_id = fields.Many2one(
        'sale.employee',
        string="Nhân viên phụ trách",
        domain=[('role_ids.code', '=', 'sales')]
    )

    type = fields.Selection([
        ('individual', 'Cá nhân'),
        ('broker', 'Môi giới'),
        ('investor', 'Nhà đầu tư'),
        ('company', 'Doanh nghiệp'),
    ], string="Phân loại khách")

    status = fields.Selection([
        ('new', 'Khách mới'),
        ('active', 'Đang tương tác'),
        ('inactive', 'Không còn tương tác'),
        ('blacklist', 'Blacklist'),
    ], default='new', string="Trạng thái")

    tier = fields.Selection([
        ('normal', 'Thông thường'),
        ('vip', 'Thân thiết'),
    ], default='normal', string="Phân hạng")

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

