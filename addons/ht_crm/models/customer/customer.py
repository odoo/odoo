from odoo import models, fields, api, exceptions
import xlsxwriter
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)

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

    # Preview
    permanent_address_preview = fields.Char(
        compute="_compute_permanent_address_preview",
        store=False
    )
    contact_address_preview = fields.Char(
        compute="_compute_contact_address_preview",
        store=False
    )

    def send_mail(self):
        # Logic của bạn
        result = "Done"

        mail_values = {
            'subject': 'Thông báo từ Odoo',
            'body_html': """
                <p>Hàm <b>my_function</b> vừa được chạy thành công.</p>
            """,
            'email_to': 'hailuomg62@gmail.com',
            'email_from': 'noreply@example.com',
        }

        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        return result

    def button_test_odoobot(self):
        # 1. Định nghĩa nội dung tin nhắn của Bot
        message_body = f"Vui lòng kiểm tra Data!"
        
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
        

    @api.depends('permanent_address')
    def _compute_permanent_address_preview(self):
        for rec in self:
            if rec.permanent_address:
                rec.permanent_address_preview = (
                    rec.permanent_address[:30] + '...'
                    if len(rec.permanent_address) > 30
                    else rec.permanent_address
                )
            else:
                rec.permanent_address_preview = False

    @api.depends('permanent_address')
    def _compute_contact_address_preview(self):
        for rec in self:
            if rec.contact_address:
                rec.contact_address_preview = (
                    rec.contact_address[:30] + '...'
                    if len(rec.contact_address) > 30
                    else rec.contact_address
                )
            else:
                rec.contact_address_preview = False

    # Nhân viên đang phụ trách (có thể thay)
    salesperson_id = fields.Many2one(
        
        'employee.profile.sales',
        string="Nhân viên phụ trách"
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

