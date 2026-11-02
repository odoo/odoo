# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""อากรแสตมป์ (Stamp Duty) ตามประมวลรัษฎากร หมวด 6.

โมดูลนี้มี 2 โมเดล

* ``od19.stamp.duty.rate`` — บัญชีอัตราอากรแสตมป์ (ลักษณะแห่งตราสาร + อัตรา)
  ใช้กำหนดว่าแต่ละตราสารคำนวณอากรอย่างไร (อัตราตามมูลค่า หรืออัตราคงที่)
* ``od19.stamp.duty`` — รายการอากรแสตมป์ที่ต้องนำส่ง/ปิดอากร
  โดยคำนวณอากรอัตโนมัติจากอัตราที่เลือกและมูลค่าแห่งตราสาร

กติกาการคำนวณตามบัญชีอัตราอากรแสตมป์: "ทุกจำนวนเงิน X บาท หรือเศษของ X บาท"
หมายถึงปัดขึ้นเป็นจำนวนเต็มหน่วย (ceil) เช่น ค่าเช่า 5,500 บาท อัตรา 1 บาท/1,000
= ceil(5.5) = 6 บาท
"""

import math

from odoo import api, fields, models


class StampDutyRate(models.Model):
    """บัญชีอัตราอากรแสตมป์ (ลักษณะแห่งตราสาร)."""

    _name = "od19.stamp.duty.rate"
    _description = "Stamp Duty Rate (บัญชีอัตราอากรแสตมป์)"
    _order = "code, id"

    name = fields.Char(
        string="ลักษณะแห่งตราสาร",
        required=True,
        help="ชื่อประเภทตราสารตามบัญชีอัตราอากรแสตมป์",
    )
    code = fields.Char(
        string="ลักษณะที่",
        help="ลำดับลักษณะแห่งตราสารตามบัญชีอัตราอากรแสตมป์ (1-28)",
    )
    rate_type = fields.Selection(
        [
            ("scale", "อัตราตามมูลค่าตราสาร"),
            ("fixed", "อัตราคงที่ต่อฉบับ"),
        ],
        string="รูปแบบอัตรา",
        required=True,
        default="scale",
    )
    rate_amount = fields.Monetary(
        string="อัตราอากร (บาท)",
        required=True,
        default=1.0,
        currency_field="currency_id",
        help="จำนวนอากรต่อหนึ่งหน่วยฐาน หรืออากรคงที่ต่อฉบับ",
    )
    base_unit = fields.Monetary(
        string="หน่วยฐาน (บาท)",
        default=1000.0,
        currency_field="currency_id",
        help="หน่วยของมูลค่าตราสารที่ใช้อัตรา เช่น 1,000 บาท หรือ 2,000 บาท",
    )
    max_amount = fields.Monetary(
        string="อากรสูงสุด (บาท)",
        currency_field="currency_id",
        help="เพดานอากรต่อตราสาร 1 ฉบับ (0 = ไม่จำกัด)",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    notes = fields.Text(string="หมายเหตุ")
    active = fields.Boolean(default=True)


class StampDuty(models.Model):
    """รายการอากรแสตมป์."""

    _name = "od19.stamp.duty"
    _description = "Stamp Duty (รายการอากรแสตมป์)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "instrument_date desc, id desc"

    name = fields.Char(
        string="เลขที่รายการ",
        required=True,
        copy=False,
        default="/",
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="คู่สัญญา",
        help="คู่สัญญาที่เกี่ยวข้องกับตราสาร",
    )
    rate_id = fields.Many2one(
        "od19.stamp.duty.rate",
        string="ลักษณะแห่งตราสาร",
        required=True,
        ondelete="restrict",
    )
    rate_code = fields.Char(
        string="ลักษณะที่",
        related="rate_id.code",
        store=True,
    )
    document_reference = fields.Char(string="เลขที่ตราสาร")
    instrument_date = fields.Date(
        string="วันที่ตราสาร",
        required=True,
        default=fields.Date.context_today,
    )
    base_amount = fields.Monetary(
        string="มูลค่าแห่งตราสาร (บาท)",
        currency_field="currency_id",
        help="มูลค่าที่ใช้อ้างอิงในการคำนวณอากร (ค่าเช่า/สินจ้าง/ยอดเงินกู้)",
    )
    duty_amount = fields.Monetary(
        string="อากรที่ต้องชำระ (บาท)",
        currency_field="currency_id",
        compute="_compute_duty_amount",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "ร่าง"),
            ("paid", "ปิดอากรแล้ว"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
    )
    note = fields.Html(string="บันทึกช่วยจำ")

    @api.depends("rate_id", "rate_id.rate_type", "rate_id.rate_amount",
                 "rate_id.base_unit", "rate_id.max_amount", "base_amount")
    def _compute_duty_amount(self):
        for rec in self:
            duty = 0.0
            rate = rec.rate_id
            if rate:
                if rate.rate_type == "fixed":
                    duty = rate.rate_amount
                elif rate.base_unit:
                    # A negative instrument value is invalid; clamp it so the
                    # duty can never become negative.
                    base = max(rec.base_amount or 0.0, 0.0)
                    units = math.ceil(base / rate.base_unit)
                    duty = units * rate.rate_amount
                if rate.max_amount and duty > rate.max_amount:
                    duty = rate.max_amount
            rec.duty_amount = duty

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "od19.stamp.duty"
                ) or "/"
        return super().create(vals_list)

    def action_mark_paid(self):
        self.write({"state": "paid"})

    def action_reset_draft(self):
        self.write({"state": "draft"})
