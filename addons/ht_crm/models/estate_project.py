from odoo import models, fields, api

class EstateProject(models.Model):
    _name = 'estate.project'
    _description = 'Dự án Bất động sản'

    name = fields.Char(string="Tên dự án", required=True)
    investor = fields.Char(string="Chủ đầu tư")
    location = fields.Char(string="Vị trí")

    area = fields.Float(string="Diện tích (ha)")
    price_per_m2 = fields.Float(string="Giá bán (VND/m²)")

    legal_status = fields.Selection([
        ('pink_book', 'Sổ hồng'),
        ('red_book', 'Sổ đỏ'),
        ('sale_contract', 'Hợp đồng mua bán'),
        ('pending', 'Đang cập nhật')
    ], string="Pháp lý")

    progress = fields.Selection([
        ('planning', 'Quy hoạch'),
        ('launching', 'Sắp mở bán'),
        ('under_construction', 'Đang xây dựng'),
        ('completed', 'Đã hoàn thành')
    ], string="Tiến độ")

    note = fields.Text(string="Ghi chú")

    customer_ids = fields.Many2many(
        'sale.customer',
        string="Khách hàng quan tâm"
    )