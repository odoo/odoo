from odoo import models, fields, api, exceptions
from datetime import date

class Transaction(models.Model):
    _name = 'sale.transaction'
    _description = "Transaction Information"

    name = fields.Char(
        string='Mã giao dịch',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Đơn vị tiền tệ",
        default=lambda self: self.env.company.currency_id,
    )

    employee_id = fields.Many2one('sale.employee', string="Sales", domain=[('role_ids.code', '=', 'sales')], required=True)
    customer_id = fields.Many2one("sale.customer", string="Khách hàng", required=True)
    
    date = fields.Date(default=fields.Date.today, string="Ngày giao dịch")

    # Thông tin liên quan về SP
    project_id = fields.Many2one(related='product_id.project_id', string="Dự án")
    product_id = fields.Many2one('estate.property.unit', string="Tên SP", domain=[('state', 'in', ['available', 'resale'])], required=True)
    net_area = fields.Float(
        related="product_id.net_area",
        string="Diện tích thông thủy (m²)",
        store=True,
        readonly=True
    )

    gross_area = fields.Float(
        related="product_id.gross_area",
        string="Diện tích tim tường (m²)",
        store=True,
        readonly=True
    )

    # % VAT
    vat_percent = fields.Float(
        string="VAT (%)",
        default=0,
        digits=(16, 1)
    )

    # Tiền VAT
    vat_amount = fields.Monetary(
        string="Tiền VAT",
        currency_field="currency_id",
        compute="_compute_amount",
        store=True
    )

    hot_money = fields.Monetary(
        string="Thưởng nóng",
        currency_field="currency_id",
    )

    # Nhập tay
    discount_amount = fields.Monetary(
        string="Tiền chiết khấu",
        currency_field="currency_id"
    )

    # Giá sau chiết khấu (chưa VAT)
    price_subtotal = fields.Monetary(
        string="Giá sau chiết khấu",
        currency_field="currency_id",
        compute="_compute_amount",
        store=True
    )

    # Tổng thanh toán cuối
    price_total = fields.Monetary(
        string="Tổng thanh toán",
        currency_field="currency_id",
        compute="_compute_amount",
        store=True
    )

    # Trường bổ sung
    listed_price = fields.Monetary(
        currency_field="currency_id",
        related="product_id.price",
        string="Giá niêm yết",
        store=True,
        readonly=True
    )

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('booking', 'Giữ chỗ'),
        ('deposit', 'Đặt cọc'),
        ('cancel', 'Hủy'),
    ], default='draft')

    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Hồ sơ hợp đồng'
    )

    @api.constrains('discount')
    def _check_discount(self):
        for record in self:
            if record.discount < 0 or record.discount > 100:
                raise exceptions.ValidationError("Chiết khấu phải nằm trong khoảng từ 0 đến 100%.")

    @api.depends(
        'listed_price',
        'discount_amount',
        'vat_percent'
    )
    def _compute_amount(self):
        for rec in self:

            # Giá sau CK
            rec.price_subtotal = (
                rec.listed_price -
                rec.discount_amount
            )

            # VAT
            rec.vat_amount = (
                rec.price_subtotal *
                rec.vat_percent / 100
            )

            # Tổng cuối
            rec.price_total = (
                rec.price_subtotal +
                rec.vat_amount
            )

    @api.depends('listed_price', 'discount_amount')
    def _compute_final_price(self):
        for rec in self:
            discount_amount = rec.listed_price * (rec.discount / 100)
            rec.price_total = rec.listed_price - discount_amount

    @api.depends('tax')
    def _compute_final_price(self):
        for rec in self:
            rec.tax_amount = rec.listed_price * (rec.discount / 100)

    def _get_kpi(self, employee_id, month, year):
        return self.env['sale.employee.kpi'].search([
            ('employee_id', '=', employee_id),
            ('month', '=', month),
            ('year', '=', year),
        ], limit=1)

    def _increase_kpi(self, employee_id, month, year, value):
        kpi_model = self.env['sale.employee.kpi']
        kpi = self._get_kpi(employee_id, month, year)

        if kpi:
            kpi.write({
                'total_value': kpi.total_value + value,
                'total_deals': kpi.total_deals + 1,
            })
        else:
            kpi_model.create({
                'employee_id': employee_id,
                'month': month,
                'year': year,
                'total_value': value,
                'total_deals': 1,
            })

    def _decrease_kpi(self, employee_id, month, year, value):
        kpi = self._get_kpi(employee_id, month, year)

        if not kpi:
            return

        new_value = max(kpi.total_value - value, 0)
        new_deals = max(kpi.total_deals - 1, 0)

        if new_deals == 0:
            kpi.unlink()
        else:
            kpi.write({
                'total_value': new_value,
                'total_deals': new_deals,
            })

    def action_print_transaction(self):
        self.ensure_one()

        return self.env.ref(
            'ht_crm.action_report_transaction'
        ).report_action(self)


    # ================= CREATE =================
    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sale.transaction'
                ) or 'New'

        records = super().create(vals_list)

        for record in records:
            if record.employee_id and record.date:
                date = fields.Date.from_string(record.date)

                self._increase_kpi(
                    record.employee_id.id,
                    date.month,
                    date.year,
                    record.price_total
                )

        return records

    # ================= UNLINK =================
    def unlink(self):
        for record in self:
            if record.employee_id and record.date:
                self._decrease_kpi(
                    record.employee_id.id,
                    record.date.month,
                    record.date.year,
                    record.price_total
                )

        return super().unlink()


    # ================= WRITE =================
    def write(self, vals):
        # 🔹 Step 1: lưu trạng thái cũ
        old_data = {
            rec.id: {
                'employee_id': rec.employee_id.id,
                'month': rec.date.month if rec.date else False,
                'year': rec.date.year if rec.date else False,
                'value': rec.price_total,
            }
            for rec in self
        }

        # 🔹 Step 2: write
        res = super().write(vals)

        # 🔹 Step 3: trừ KPI cũ
        for rec in self:
            old = old_data.get(rec.id)

            if old and old['employee_id'] and old['month']:
                self._decrease_kpi(
                    old['employee_id'],
                    old['month'],
                    old['year'],
                    old['value']
                )

        # 🔹 Step 4: cộng KPI mới
        for rec in self:
            if rec.employee_id and rec.date:
                self._increase_kpi(
                    rec.employee_id.id,
                    rec.date.month,
                    rec.date.year,
                    rec.price_total
                )
        return res
    

# class PaymentPlanLine(models.Model):
#     _name = "sale.transaction.payment"
#     _description = "Chi Tiết Đợt TT"
#     _order = "sequence, id"

#     currency_id = fields.Many2one(
#         'res.currency',
#         string="Đơn vị tiền tệ",
#         default=lambda self: self.env.company.currency_id,
#     )
    
#     sequence = fields.Integer(default=10) 

#     transaction_id = fields.Many2one("sale.transaction", string="Mã giao dịch")

#     name = fields.Char(
#         required=True,
#         help="Ví dụ: Đợt 1, Đợt 2..."
#     )

#     payment_type = fields.Selection([
#         ("deposit", "Đặt cọc"),
#         ("installment", "Thanh toán"),
#         ("handover", "Bàn giao"),
#         ("ownership", "Ra sổ"),
#     ], default="installment", string="Loại")

#     due_date = fields.Date(
#         string="Ngày đến hạn"
#     )

#     payment_method = fields.Selection([
#         ("fixed", "Số tiền cố định"),
#         ("percent", "Theo tỷ lệ"),
#     ], default="percent", string="Hình thức thanh toán")

#     fixed_amount = fields.Monetary(
#         string="Số tiền cố định",
#         currency_field="currency_id"
#     )

#     amount = fields.Monetary(
#         string="Số tiền phải trả",
#         currency_field="currency_id",
#         compute="_compute_amount",
#         store=True
#     )

#     paid_amount = fields.Monetary(
#         string="Đã trả",
#         currency_field="currency_id",
#     )

#     percent = fields.Float(
#         string="Tỷ lệ (%)"
#     )

#     status = fields.Selection([
#         ('pending', 'Chờ thanh toán'),
#         ('paid', 'Đã thanh toán'),
#         ('overdue', 'Quá hạn')
#     ], compute="_compute_status", store=True, string="Trạng thái")

#     @api.depends(
#         'payment_method',
#         'percent',
#         'fixed_amount',
#         'transaction_id.product_id.price'
#     )
#     def _compute_amount(self):
#         for rec in self:

#             if rec.payment_method == 'percent':

#                 product_price = rec.transaction_id.price_subtotal or 0.0

#                 rec.fixed_amount = 0

#                 rec.amount = (
#                     product_price * rec.percent / 100
#                 )

#             else:
#                 rec.amount = rec.fixed_amount

#     @api.depends('amount', 'paid_amount', 'due_date')
#     def _compute_status(self):
#         today = fields.Date.today()

#         for rec in self:
#             # Đã thanh toán đủ
#             if rec.amount > 0 and rec.paid_amount >= rec.amount:
#                 rec.status = 'paid'

#             # Quá hạn
#             elif (
#                 rec.due_date
#                 and rec.due_date < today
#                 and rec.paid_amount < rec.amount
#             ):
#                 rec.status = 'overdue'

#             # Chờ thanh toán
#             else:
#                 rec.status = 'pending'


#     @api.constrains('amount', 'paid_amount', 'status')
#     def _check_payment_amount(self):
#         for rec in self:
#             # Không âm
#             if rec.amount < 0:
#                 raise exceptions.ValidationError("Số tiền phải trả không được âm.")

#             if rec.paid_amount < 0:
#                 raise exceptions.ValidationError("Số tiền đã trả không được âm.")

#             # Không trả vượt
#             if rec.paid_amount > rec.amount:
#                 raise exceptions.ValidationError("Số tiền đã trả không được lớn hơn số tiền phải trả.")

#             # Status paid thì phải trả đủ
#             if rec.status == 'paid' and rec.paid_amount < rec.amount:
#                 raise exceptions.ValidationError("Không thể chuyển sang Đã thanh toán khi chưa trả đủ.")