# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model
    def _prepare_from_pos(self, sequence, order_line_data):
        return {
            "sequence": sequence,
            "product_id": order_line_data["product_id"],
            "product_uom_qty": order_line_data["qty"],
            "discount": order_line_data["discount"],
            "price_unit": order_line_data["price_unit"],
            "tax_id": order_line_data["tax_ids"],
        }

    def _get_sale_order_line_multiline_description_sale(self):
        res = super()._get_sale_order_line_multiline_description_sale()

        for sequence, line_data in enumerate(
            self.env.context.get("pos_order_lines_data", []), start=1
        ):
            if line_data.get("customer_note", False) and self.sequence == sequence:
                res += f"\n{line_data.get('customer_note')}"

        return res
