from odoo import models, fields, api, exceptions
import datetime
from dateutil.relativedelta import relativedelta

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

    employee_id = fields.Many2one('employee.profile.sales', string="Sales", required=True)
    customer_id = fields.Many2one("sale.customer", string="Khách hàng", required=True)
    
    date = fields.Date(default=fields.Date.today, string="Ngày giao dịch")
    plan_id = fields.Many2one('estate.payment.plan', string="Phương thức thanh toán")
    payment_ids = fields.One2many('sale.transaction.payment', "transaction_id", string="Chi tiết thanh toán")

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


    def _generate_payment_lines(self):
        for rec in self:

            lines = [(5, 0, 0)]

            if not rec.plan_id:
                rec.payment_ids = lines
                continue

            for installment in rec.plan_id.installment_ids.sorted(
                key=lambda x: x.sequence
            ):

                lines.append((0, 0, {
                    "plan_line_id": installment.id,
                }))

            rec.payment_ids = lines


    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        for rec in self:

            if not rec.plan_id:
                rec.payment_ids = [(5, 0, 0)]
                continue

            # tránh generate lại nếu đã đúng plan
            if rec.payment_ids:
                continue

            lines = []

            for installment in rec.plan_id.installment_ids.sorted(
                key=lambda x: x.sequence
            ):
                lines.append((0, 0, {
                    "plan_line_id": installment.id,
                }))

            rec.payment_ids = lines

    @api.depends('listed_price', 'discount_amount','vat_percent')
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
        records.filtered("plan_id")._generate_payment_lines()

        return records

    # ================= UNLINK =================


    # ================= WRITE =================
    def write(self, vals):
        res = super().write(vals)

        if "plan_id" in vals:
            self.filtered("plan_id")._generate_payment_lines()

        return res
    

class TransactionPayment(models.Model):
    _name = "sale.transaction.payment"
    _description = "Chi Tiết TT Mẫu"
    _order = "sequence, id"

    currency_id = fields.Many2one(
        'res.currency',
        string="Đơn vị tiền tệ",
        default=lambda self: self.env.company.currency_id,
    )
    
    sequence = fields.Integer(related='plan_line_id.sequence') 

    transaction_id = fields.Many2one("sale.transaction", string="Mã giao dịch")
    plan_line_id = fields.Many2one(
        "estate.payment.plan.line",
        string="Đợt mẫu"
    )

    name = fields.Char(related="plan_line_id.name")

    # Chỉ đọc
    due_type = fields.Selection(related="plan_line_id.due_type", string="Xét theo")
    due_value = fields.Integer(related="plan_line_id.due_value", string="Sau bao lâu")

    # === #
    base_date = fields.Date(
        string="Ngày gốc",
        compute="_compute_due_date",
        inverse="_inverse_base_date",
        store=True,
    )
            
    due_date = fields.Date(
        string="Ngày đến hạn",
        compute="_compute_due_date",
        store=True,
    )

    amount = fields.Monetary(currency_field='currency_id', string="Số tiền phải trả", compute="_compute_amount", store=True)
    paid_amount = fields.Monetary(currency_field='currency_id', string="Đã trả")

    status = fields.Selection([
        ('pending', 'Chờ thanh toán'),
        ('paid', 'Đã thanh toán'),
        ('overdue', 'Quá hạn')
    ], compute="_compute_status", store=True, string="Trạng thái")


    def _inverse_base_date(self):
        pass

    @api.depends(
        "transaction_id.date",
        "transaction_id.payment_ids.due_date",
        "sequence",
    )
    def _compute_base_date(self):
        for rec in self:

            rec.base_date = rec.transaction_id.date

            if not rec.transaction_id:
                continue

            previous_lines = rec.transaction_id.payment_ids.filtered(
                lambda x:
                    x.sequence < rec.sequence
                    and x.id != rec.id
            ).sorted("sequence")

            if previous_lines:
                rec.base_date = previous_lines[-1].due_date

    @api.depends(
        "transaction_id.date",
        "transaction_id.payment_ids.due_type",
        "transaction_id.payment_ids.due_value",
        "transaction_id.payment_ids.sequence",
    )
    def _compute_due_date(self):

        transactions = self.mapped("transaction_id")

        for transaction in transactions:

            lines = transaction.payment_ids.sorted(
                lambda x: (x.sequence, x.id)
            )

            base_date = transaction.date

            for line in lines:

                line.base_date = base_date

                line.due_date = False

                if not base_date:
                    continue

                if line.due_type == "day":
                    line.due_date = (
                        base_date +
                        datetime.timedelta(days=line.due_value)
                    )

                elif line.due_type == "month":
                    line.due_date = (
                        base_date +
                        relativedelta(months=line.due_value)
                    )

                # next line base_date
                if line.due_date:
                    base_date = line.due_date

    @api.depends("plan_line_id")
    def _compute_amount(self):
        for rec in self:

            if rec.plan_line_id.payment_method == 'percent':

                product_price = rec.transaction_id.price_subtotal or 0.0

                rec.amount = (
                    product_price * (rec.plan_line_id.percent / 100)
                )

            else:
                rec.amount = rec.plan_line_id.amount
            


    @api.constrains('amount', 'paid_amount', 'status')
    def _check_payment_amount(self):
        for rec in self:
            # Không âm
            if rec.amount < 0:
                raise exceptions.ValidationError("Số tiền phải trả không được âm.")

            if rec.paid_amount < 0:
                raise exceptions.ValidationError("Số tiền đã trả không được âm.")

            # Không trả vượt
            if rec.paid_amount > rec.amount:
                raise exceptions.ValidationError("Số tiền đã trả không được lớn hơn số tiền phải trả.")

            # Status paid thì phải trả đủ
            if rec.status == 'paid' and rec.paid_amount < rec.amount:
                raise exceptions.ValidationError("Không thể chuyển sang Đã thanh toán khi chưa trả đủ.")
            
    @api.depends('amount', 'paid_amount', 'due_date')
    def _compute_status(self):
        today = fields.Date.today()

        for rec in self:
            # Đã thanh toán đủ
            if rec.amount > 0 and rec.paid_amount >= rec.amount:
                rec.status = 'paid'

            # Quá hạn
            elif (
                rec.due_date
                and rec.due_date < today
                and rec.paid_amount < rec.amount
            ):
                rec.status = 'overdue'

            # Chờ thanh toán
            else:
                rec.status = 'pending'
