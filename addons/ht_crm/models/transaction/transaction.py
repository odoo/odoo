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
        default=lambda self: self.env.company.currency_id
    )

    employee_id = fields.Many2one('sale.employee', string="Sales", domain=[('role_ids.code', '=', 'sales')])
    customer_id = fields.Many2one("sale.customer", string="Khách hàng")
    
    date = fields.Date(default=fields.Date.today, string="Ngày giao dịch")

    # Thông tiên liên quan về SP
    product_id = fields.Many2one('estate.property.unit', string="Tên SP", domain=[('state', 'in', ['available', 'resale'])])
    net_area = fields.Float(
        related="product_id.net_area",
        string="DTTT (m²)",
        store=True,
        readonly=True
    )

    gross_area = fields.Float(
        related="product_id.gross_area",
        string="DTLL (m²)",
        store=True,
        readonly=True
    )

    # % chiết khấu
    discount = fields.Float(
        string="Chiết khấu (%)",
        default=0,
        digits=(16, 1)
    )

    # Giá cuối cùng sau CK
    price_total = fields.Monetary(
        string="Giá sau VAT",
        currency_field="currency_id",
        compute="_compute_final_price",
        store=True,
        digits=(16, 0)
    )

    # Trường bổ sung
    listed_price = fields.Monetary(
        currency_field="currency_id",
        related="product_id.price",
        string="Giá niêm yết",
        store=True,
        readonly=True,
        digits=(16, 0)
    )

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('booking', 'Giữ chỗ'),
        ('deposit', 'Đặt cọc'),
        ('cancel', 'Hủy'),
    ], default='draft')

    @api.constrains('discount')
    def _check_discount(self):
        for record in self:
            if record.discount < 0 or record.discount > 100:
                raise exceptions.ValidationError("Chiết khấu phải nằm trong khoảng từ 0 đến 100%.")

    @api.depends('listed_price', 'discount')
    def _compute_final_price(self):
        for rec in self:
            discount_amount = rec.listed_price * (rec.discount / 100)
            rec.price_total = rec.listed_price - discount_amount

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

    def action_confirm_deposit(self):
        for rec in self:

            if rec.product_id.state not in ['available', 'reserved']:
                raise exceptions.ValidationError(
                    "Sản phẩm không khả dụng."
                )

            rec.write({
                'state': 'deposit'
            })

            rec.product_id.write({
                'state': 'sold'
            })

    def action_confirm_booking(self):
        for rec in self:

            if rec.product_id.state not in ['available', 'reserved']:
                raise exceptions.ValidationError(
                    "Sản phẩm không khả dụng."
                )

            rec.write({
                'state': 'booking'
            })

            rec.product_id.write({
                'state': 'reserved'
            })

    def action_cancel(self):
        for rec in self:

            if rec.state == 'cancel':
                continue

            rec.write({
                'state': 'cancel'
            })

            # Mở bán lại sản phẩm
            rec.product_id.write({
                'state': 'available'
            })
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

