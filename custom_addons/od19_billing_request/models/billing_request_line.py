# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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

    qty_ordered = fields.Float(
        string="Ordered Qty / จำนวนตามต้นทาง",
        compute="_compute_quantities",
        digits="Product Unit of Measure",
    )
    qty_already_requested = fields.Float(
        string="Already Requested / แจ้งแล้ว",
        compute="_compute_quantities",
        digits="Product Unit of Measure",
    )
    qty_invoiced = fields.Float(
        string="Invoiced / ออกบิลแล้ว",
        compute="_compute_quantities",
        digits="Product Unit of Measure",
    )
    remaining_to_bill = fields.Float(
        string="Remaining to Bill / คงเหลือที่เปิดบิลได้",
        compute="_compute_quantities",
        digits="Product Unit of Measure",
    )

    @api.depends(
        "sale_line_id",
        "sale_line_id.product_uom_qty",
        "sale_line_id.qty_invoiced",
        "purchase_line_id",
        "purchase_line_id.product_qty",
        "purchase_line_id.qty_invoiced",
        "stock_move_id",
        "stock_move_id.quantity",
        "quantity",
        "request_id.state",
    )
    def _compute_quantities(self):
        for line in self:
            if line.sale_line_id:
                line.qty_ordered = line.sale_line_id.product_uom_qty
                line.qty_invoiced = line.sale_line_id.qty_invoiced
            elif line.purchase_line_id:
                line.qty_ordered = line.purchase_line_id.product_qty
                line.qty_invoiced = line.purchase_line_id.qty_invoiced
            elif line.stock_move_id:
                line.qty_ordered = line.stock_move_id.quantity
                line.qty_invoiced = 0.0
            else:
                line.qty_ordered = 0.0
                line.qty_invoiced = 0.0
            line.qty_already_requested = line._od19_qty_already_requested()
            line.remaining_to_bill = max(
                line.qty_ordered - line.qty_already_requested - line.quantity, 0.0
            )

    def _od19_qty_already_requested(self):
        """ผลรวม quantity ของบรรทัดอื่นที่อ้างต้นทางบรรทัดเดียวกัน (ไม่นับตัวเอง)."""
        self.ensure_one()
        domain = [
            ("id", "!=", self.id),
            ("request_id.state", "in", ("draft", "submitted", "invoiced")),
        ]
        if self.sale_line_id:
            domain.append(("sale_line_id", "=", self.sale_line_id.id))
        elif self.purchase_line_id:
            domain.append(("purchase_line_id", "=", self.purchase_line_id.id))
        elif self.stock_move_id:
            domain.append(("stock_move_id", "=", self.stock_move_id.id))
        else:
            return 0.0
        others = self.env["od19.billing.request.line"].search(domain)
        return sum(others.mapped("quantity"))

    @api.constrains("quantity")
    def _check_quantity_positive(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(
                    _("Quantity must be greater than zero on every line.")
                )

    @api.constrains("quantity")
    def _check_quantity_within_remaining(self):
        for line in self:
            if not (line.sale_line_id or line.purchase_line_id or line.stock_move_id):
                continue
            # Threshold is the qty still billable *before* this line is counted,
            # i.e. ordered minus what other requests already reserved.
            available = line.qty_ordered - line.qty_already_requested
            if line.quantity > available + 1e-6:
                raise ValidationError(
                    _(
                        "Cannot bill %(qty)s: only %(remaining)s remaining on "
                        "%(product)s."
                    )
                    % {
                        "qty": line.quantity,
                        "remaining": available,
                        "product": line.product_id.display_name,
                    }
                )
