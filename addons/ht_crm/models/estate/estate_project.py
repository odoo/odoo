from odoo import models, fields, api, exceptions

class EstatePropertyUnitType(models.Model):
    _name = 'estate.property.unit.type'
    _description = 'Loại căn hộ'

    name = fields.Char(string="Tên loại", required=True)
    code = fields.Char(string="Mã")

    description = fields.Text(string="Mô tả")

class EstatePropertyUnit(models.Model):
    _name = 'estate.property.unit'
    _description = 'Căn hộ / Sản phẩm bất động sản'

    currency_id = fields.Many2one(
        'res.currency',
        string="Đơn vị tiền tệ",
        default=lambda self: self.env.company.currency_id
    )

    product_code = fields.Char(
        string="Mã sản phẩm",
        compute="_compute_product_code",
        inverse="_inverse_product_code",
        store=True,
        required=True,
    )
    project_id = fields.Many2one(
        'estate.project',
        string="Dự án",
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(related="product_code")

    block = fields.Char(string="Block", size=20)
    floor = fields.Integer(string="Tầng")
    unit_number = fields.Integer(string="Căn hộ số")

    unit_type_id = fields.Many2one(
        'estate.property.unit.type',
        string="Loại căn hộ"
    )

    net_area = fields.Float(string="Diện tích thông thủy (m²)")   # diện tích thông thủy
    gross_area = fields.Float(string="Diện tích tim tường (m²)") # diện tích tim tường

    priority = fields.Integer(string="Ưu tiên", default=1)

    # Trường bổ sung
    price = fields.Monetary(string="Giá bán", currency_field="currency_id")
    state = fields.Selection([
        ('available', 'Còn trống'),
        ('reserved', 'Giữ chỗ'),
        ('sold', 'Đã bán'),
        ('resale', 'Bán lại'),
        ('blocked', 'Khoá')
    ], default='available', string="Trạng thái")


    @api.depends('block', 'floor', 'unit_number')
    def _compute_product_code(self):
        for rec in self:
            unit_block = rec.block or ""

            unit_floor = f"{rec.floor:02d}"
            unit_no = f"{rec.unit_number:02d}"

            if unit_block and unit_floor and unit_no:
                rec.product_code = f"{unit_block}-{unit_floor}-{unit_no}"
            else:
                rec.product_code = ""
    
    def _inverse_product_code(self):
        for rec in self:
            if rec.product_code:
                parts = rec.product_code.split("-")

                if len(parts) == 3:
                    rec.block = parts[0]
                    rec.floor = int(parts[1])
                    rec.unit_number = int(parts[2])

    # Ràng buộc
    @api.constrains('floor')
    def _check_floor_non_negative(self):
        for rec in self:
            if rec.floor is not None and rec.floor < 0 and rec.floor > 99:
                raise exceptions.ValidationError("Tầng phải nằm trong khoảng 0 tới 99!")
            
    @api.constrains('price')
    def _check_price_non_negative(self):
        for rec in self:
            if rec.price is not None and rec.price < 0:
                raise exceptions.ValidationError("Giá trị không được nhỏ hơn 0!")
            
    @api.constrains('net_area', 'gross_area')
    def _check_area_valid(self):
        for rec in self:
            if rec.net_area < 0:
                raise exceptions.ValidationError("Diện tích thông thủy không được nhỏ hơn 0!")

            if rec.gross_area < 0:
                raise exceptions.ValidationError("Diện tích tim tường không được nhỏ hơn 0!")

            if rec.gross_area and rec.net_area and rec.gross_area < rec.net_area:
                raise exceptions.ValidationError(
                    "Diện tích tim tường phải lớn hơn hoặc bằng diện tích thông thủy!"
                )

class EstateProjectPromotion(models.Model):
    _name = 'estate.project.promotion'
    _description = 'Ưu đãi dự án'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)

    active = fields.Boolean(default=True)

    project_id = fields.Many2one(
        'estate.project',
        required=True,
        ondelete='cascade',
        string="Dự án"
    )

    name = fields.Char(
        required=True,
        string="Tên ưu đãi"
    )

    promotion_type = fields.Selection([
        ('cash', 'Tiền mặt'),
        ('percent', 'Phần trăm'),
        ('gift', 'Quà tặng'),
        ('other', 'Khác'),
    ], required=True, default='cash')

    cash_amount = fields.Monetary(string="Trị giá")
    percent_amount = fields.Float(string="Phần trăm ưu đãi", digits=(16,1))

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id.id
    )

    start_date = fields.Date(string="Từ ngày")
    end_date = fields.Date(string="Đến ngày")

    note = fields.Text(string="Ghi chú")

class EstateProject(models.Model):
    _name = 'estate.project'
    _description = 'Dự án Bất động sản'

    # Trường cơ bản
    name = fields.Char(string="Tên dự án", required=True)
    investor = fields.Char(string="Chủ đầu tư")
    location = fields.Char(string="Vị trí")

    area = fields.Float(string="Diện tích (ha)")
    price_per_m2 = fields.Float(string="Giá bán (VND/m²)")

    # Trường bổ sung
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

    # Các trường liên kết
    payment_plans = fields.One2many("estate.payment.plan", "project_id", string="Phương thức thanh toán")

    phonebook_ids = fields.One2many(
        "sale.phonebook",
        "project_id",
        string="Data",
        groups="ht_crm.group_ht_board_of_directors,ht_crm.group_ht_executive"
    )

    purchased_customer_ids = fields.Many2many(
        'sale.customer',
        'estate_project_purchased_rel',
        'project_id',
        'customer_id',
        string="Khách hàng đã mua"
    )

    interested_customer_ids = fields.Many2many(
        'sale.customer',
        'estate_project_interested_rel',
        'project_id',
        'customer_id',
        string="Khách hàng quan tâm"
    )

    unique_sales_ids = fields.Many2many(
        'employee.profile.sales',
        compute='_compute_unique_sales',
        string='Sales phụ trách'
    )

    sales_ids = fields.One2many(
        'employee.project.rel',
        'project_id',
        string="Sales phụ trách",
        groups="ht_crm.group_ht_board_of_directors,ht_crm.group_ht_executive"
    )

    unit_ids = fields.One2many(
        'estate.property.unit',
        'project_id',
        string="Rổ hàng",
        domain=[('state', 'in', ['available', 'resale'])]
    )

    promotion_ids = fields.One2many(
        'estate.project.promotion',
        'project_id',
        string="Ưu đãi"
    )

    @api.depends('sales_ids.sales_id')
    def _compute_unique_sales(self):
        for rec in self:
            rec.unique_sales_ids = rec.sales_ids.mapped('sales_id')


class EmployeeProjectRel(models.Model):
    _name='employee.project.rel'
    _description = 'Sales Assignment By Project Batch'
    _order = "project_id, sales_id"

    sales_id = fields.Many2one('employee.profile.sales', required=True, string="Sales phụ trách", ondelete='cascade')
    project_id = fields.Many2one(
        related='batch_id.project_id'
    )

    batch_id = fields.Many2one('sale.phonebook.batch', required=True, string="Tập dữ liệu", ondelete='cascade')

    phone_received = fields.Integer(string="Số đã nhận", compute='_compute_phone_received', store=True)

    @api.depends(
        'batch_id.phone_ids',
        'batch_id.phone_ids.salesperson_id'
    )
    def _compute_phone_received(self):
        for rec in self:
            rec.phone_received = len(
                rec.batch_id.phone_ids.filtered(
                    lambda p: p.salesperson_id == rec.sales_id
                )
            )

    @api.depends(
        'batch_id.phone_ids',
        'batch_id.phone_ids.salesperson_id'
    )
    def _compute_phone_received(self):
        for rec in self:
            rec.phone_received = len(
                rec.batch_id.phone_ids.filtered(
                    lambda p: p.salesperson_id == rec.sales_id
                )
            )
 

    def get_total_phone_received(self, salesperson):
        rels = self.env['employee.project.rel'].search([
            ('sales_id', '=', salesperson.id)
        ])

        return sum(rels.mapped('phone_received'))
               

    @api.constrains('sales_id', 'project_id', 'batch_id')
    def _check_unique_combination(self):
        for rec in self:
            duplicate = self.search([
                ('sales_id', '=', rec.sales_id.id),
                ('project_id', '=', rec.project_id.id),
                ('batch_id', '=', rec.batch_id.id),
                ('id', '!=', rec.id),
            ], limit=1)

            if duplicate:
                raise exceptions.ValidationError(
                    "Thông tin phân bổ này đã tồn tại!"
                )