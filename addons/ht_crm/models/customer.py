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
    id_number = fields.Char(string="CMND / Passport")
    issue_date = fields.Date(string="Ngày cấp")
    issue_place = fields.Char(string="Nơi cấp")
    permanent_address = fields.Text(string="Địa chỉ thường trú")
    contact_address = fields.Text(string="Địa chỉ liên lạc")

    phone = fields.Char(string="Số điện thoại")
    email = fields.Char(string="Email")

    # Nhân viên đang phụ trách
    salesperson_id = fields.Many2one(
        'sale.employee',
        string="Nhân viên phụ trách",
        domain=[('role_ids.code', '=', 'sales')]
    )

    # Danh sách nhân viên đã từng phụ trách
    previous_salesperson_ids = fields.Many2many(
        'sale.employee',
        string="Lịch sử phụ trách",
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

    def action_export_state_pie_excel(self):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet("Customer State")

        # Group dữ liệu giống pie chart
        data = self.read_group(
            [],
            [],
            ['state']
        )

        sheet.write(0, 0, "State")
        sheet.write(0, 1, "Count")

        row = 1
        for line in data:
            label = dict(self._fields['state'].selection).get(line['state'], line['state'])
            sheet.write(row, 0, label)
            sheet.write(row, 1, line['__count'])
            row += 1

        # ===== PIE CHART =====
        chart = workbook.add_chart({'type': 'pie'})

        chart.add_series({
            'categories': ['Customer State', 1, 0, row-1, 0],
            'values':     ['Customer State', 1, 1, row-1, 1],
        })

        chart.set_title({'name': 'Customer State Distribution'})
        sheet.insert_chart('D2', chart)

        workbook.close()
        output.seek(0)

        return {
            'type': 'ir.actions.act_url',
            'url': 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,' + output.getvalue().hex(),
            'target': 'self'
        }