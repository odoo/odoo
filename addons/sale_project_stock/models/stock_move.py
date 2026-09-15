from odoo import fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_is_zero

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _sale_get_invoice_price(self, order):
        self.check_singleton()

        if self.product_id.expense_policy == "sales_price":
            _debug.logic("reinvoice_price", move=self, by="pricelist")
            return order.pricelist_id._get_product_price(
                self.product_id,
                1.0,
                uom=self.product_uom_id,
                date=order.date_order,
            )

        uom_precision_digits = self.env["decimal.precision"].get_precision(
            "Product Unit"
        )
        if float_is_zero(self.quantity, precision_digits=uom_precision_digits):
            _debug.logic("reinvoice_price", move=self, by="zero_quantity")
            return 0.0

        price_unit = self.product_id.standard_price
        if (
            self.company_id.currency_id
            and price_unit
            and self.company_id.currency_id == order.currency_id
        ):
            _debug.logic("reinvoice_price", move=self, by="standard_price")
            return self.company_id.currency_id.round(price_unit)

        currency_id = self.company_id.currency_id
        if currency_id and currency_id != order.currency_id:
            price_unit = currency_id._convert(
                price_unit,
                order.currency_id,
                order.company_id,
                order.date_order or fields.Date.today(),
            )
        return price_unit

    def _sale_prepare_sale_line_values(self, order, price, last_sequence):
        self.check_singleton()

        order = order.sudo()
        fpos = (
            order.fiscal_position_id
            or order.fiscal_position_id._get_fiscal_position(order.partner_id)
        )
        product_taxes = self.product_id.sudo().taxes_id._filter_taxes_by_company(
            order.company_id
        )
        taxes = fpos.map_tax(product_taxes)

        return {
            "order_id": order.id,
            "name": self.reference,
            "sequence": last_sequence,
            "price_unit": price,
            "tax_ids": [x.id for x in taxes],
            "discount": 0.0,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "product_qty": self.product_uom_qty,
            "qty_transferred": self.quantity,
        }

    def _prepare_new_picking_vals(self):
        return {
            **super()._prepare_new_picking_vals(),
            "project_id": self.sale_line_id.order_id.project_id.id,
        }

    def _prepare_picking_vals(self, picking):
        return {
            **super()._prepare_picking_vals(picking),
            "project_id": self[:1].sale_line_id.order_id.project_id.id,
        }

    def _prepare_procurement_vals(self):
        res = super()._prepare_procurement_vals()
        project = self.sale_line_id.order_id.project_id
        if project:
            res["project_id"] = project.id
        return res
