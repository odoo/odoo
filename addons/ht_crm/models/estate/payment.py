from odoo import models, fields, api, exceptions
import datetime
from dateutil.relativedelta import relativedelta

class PaymentPlan(models.Model):
    _name = "estate.payment.plan"
    _description = "Phương Thức TT"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    note = fields.Text()

    project_id = fields.Many2one("estate.project", string="Dự án")
    transaction_ids = fields.One2many("sale.transaction", "plan_id", string="Giao dịch")

    installment_ids = fields.One2many(
        "estate.payment.plan.line",
        "plan_id",
        string="Chi tiết thanh toán"
    )

class PaymentPlanLine(models.Model):
    _name = "estate.payment.plan.line"
    _description = "Chi Tiết TT"
    _order = "plan_id, sequence"

    currency_id = fields.Many2one(
        'res.currency',
        string="Đơn vị tiền tệ",
        default=lambda self: self.env.company.currency_id,
    )

    plan_id = fields.Many2one("estate.payment.plan")

    sequence = fields.Integer()
    name = fields.Char(string="Đợt thanh toán", help="VD: đợt 1, đợt 2, đợt...")

    payment_method = fields.Selection([
        ("fixed", "Số tiền cố định"),
        ("percent", "Theo tỷ lệ"),
    ])

    percent = fields.Float(string="Phần trăm")

    amount = fields.Monetary(
        string="Số tiền",
        currency_field="currency_id"
    )

    due_type = fields.Selection([
        ("day", "Theo ngày"),
        ("month", "Theo tháng"),
    ], default="day")

    due_value = fields.Integer(string="Sau bao lâu")

    @api.depends("base_date", "due_type", "due_value")
    def _compute_due_date(self):
        for rec in self:

            rec.due_date = False

            if not rec.base_date:
                continue

            if rec.due_type == "day":
                rec.due_date = rec.base_date + datetime.timedelta(days=rec.due_value)

            elif rec.due_type == "month":
                rec.due_date = rec.base_date + relativedelta(months=rec.due_value)

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        for rec in self:

            if rec.payment_method == 'fixed':
                rec.percent = 0

            elif rec.payment_method == 'percent':
                rec.amount = 0