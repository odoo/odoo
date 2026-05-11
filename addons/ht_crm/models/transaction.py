from odoo import models, fields, api, exceptions
from datetime import date

class Transaction(models.Model):
    _name = 'sale.transaction'
    _description = "Transaction Information"

    name = fields.Char(
        related='transaction_code',
        store=True,
        string='Giao dịch'
    )

    transaction_code = fields.Char(
        string="Mã giao dịch", required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    employee_id = fields.Many2one('sale.employee', domain=[('role_ids.code', '=', 'sales')])
    customer_id = fields.Many2one("sale.customer")
    product_id = fields.Many2one('estate.property.unit', domain=[('state', 'in', ['available', 'resale'])])
    date = fields.Date(default=fields.Date.today)


    # BI
    value = fields.Monetary(
        string="Giá giao dịch",
        currency_field="currency_id",
        compute="_compute_value",
        store=True
    )

    # Trường bổ sung
    listed_price = fields.Float(string="Giá niêm yết")
    discount = fields.Float(
        string="Chiết khấu (%)",
        default=0,
        digits=(16, 1)
    )

    state = fields.Selection([
        ('reference', 'Tham khảo'),
        ('visit', 'Tham quan'),
        ('booking', 'Giữ chỗ'),
        ('deposit', 'Đặt cọc')
    ], string="Trạng thái", default='reference')


    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            rec.listed_price = rec.product_id.price

    @api.depends('listed_price', 'discount')
    def _compute_value(self):
        for rec in self:
            discount_amount = rec.listed_price * (rec.discount / 100)
            rec.value = rec.listed_price - discount_amount

    @api.constrains('value')
    def _check_value(self):
        for rec in self:
            if rec.value < 0:
                raise exceptions.ValidationError(("Giá trị giao dịch (%s) phải >= 0") % rec.value)

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

    # ================= CREATE =================
    @api.model
    def create(self, vals):
        record = super().create(vals)

        if record.employee_id and record.date:
            date = fields.Date.from_string(record.date)

            self._increase_kpi(
                record.employee_id.id,
                date.month,
                date.year,
                record.value
            )

        return record


    # ================= UNLINK =================
    def unlink(self):
        for record in self:
            if record.employee_id and record.date:
                self._decrease_kpi(
                    record.employee_id.id,
                    record.date.month,
                    record.date.year,
                    record.value
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
                'value': rec.value,
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
                    rec.value
                )

        return res
    