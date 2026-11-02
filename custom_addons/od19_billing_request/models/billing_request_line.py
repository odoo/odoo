# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class Od19BillingRequestLine(models.Model):
    _name = "od19.billing.request.line"
    _description = "OD19 Billing Request Line"
    _order = "request_id, sequence, id"

    request_id = fields.Many2one(
        "od19.billing.request",
        string="Request / คำขอ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        "product.product", string="Product / สินค้า", required=True
    )
    name = fields.Char(string="Description / รายละเอียด")
    product_uom_id = fields.Many2one("uom.uom", string="UoM / หน่วย")
    quantity = fields.Float(
        string="Quantity / จำนวน",
        default=1.0,
        digits="Product Unit of Measure",
        required=True,
    )
    price_unit = fields.Float(string="Unit Price / ราคาต่อหน่วย", digits="Product Price")
    discount = fields.Float(string="Discount (%)", digits="Discount")
    tax_ids = fields.Many2many("account.tax", string="Taxes / ภาษี")

    # ลิงก์บรรทัดต้นทาง
    sale_line_id = fields.Many2one("sale.order.line", string="Sale Order Line")
    purchase_line_id = fields.Many2one(
        "purchase.order.line", string="Purchase Order Line"
    )
    stock_move_id = fields.Many2one("stock.move", string="Stock Move")
    origin_line_model = fields.Char(string="Origin Line Model", readonly=True)
    origin_line_id = fields.Integer(string="Origin Line ID", readonly=True)

    # ผลลัพธ์หลังออกบิล
    target_line_id = fields.Many2one(
        "account.move.line", string="Target Line / บรรทัดปลายทาง", readonly=True
    )
