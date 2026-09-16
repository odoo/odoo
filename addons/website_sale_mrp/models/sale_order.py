from collections import defaultdict

from odoo import models
from odoo.tools import float_is_zero


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_unavailable_quantity_from_kits(self, product):
        self.check_singleton()
        unavailable_qty = 0
        if product.is_kit:
            kit_bom = (
                self.env["mrp.bom"]
                .sudo()
                ._get_bom_by_product(
                    product, company_id=self.company_id.id, bom_type="phantom"
                )[product]
            )
            _, bom_sub_lines = kit_bom._explode(product, quantity=1.0)
            unavailable_component_qties = {}
            qty_per_kit = defaultdict(float)
            for bom_line, bom_line_data in bom_sub_lines:
                if not bom_line.product_id.is_storable:
                    continue
                if float_is_zero(
                    bom_line_data["qty"],
                    precision_rounding=bom_line.product_uom_id.rounding,
                ):
                    continue
                component = bom_line.product_id
                unavailable_component_qties[component] = sum(
                    self.line_ids.filtered(
                        lambda sol, component=component: sol.product_id == component
                    ).mapped("product_uom_qty")
                )
                uom_qty_per_kit = bom_line_data["qty"] / bom_line_data["original_qty"]
                qty_per_kit[component] += bom_line.product_uom_id._get_quantity_in_unit(
                    uom_qty_per_kit / kit_bom.product_qty, component.uom_id, round=False
                )

        for line in self.line_ids:
            if not line.product_id.is_kit or line.product_id == product:
                continue
            line_kit_bom = (
                self.env["mrp.bom"]
                .sudo()
                ._get_bom_by_product(
                    line.product_id, company_id=self.company_id.id, bom_type="phantom"
                )[line.product_id]
            )
            component_qties, line_kit_qty = line_kit_bom._get_kit_component_qty(
                line.product_id
            )
            unavailable_qty += (
                component_qties.get(product, 0) * line.product_uom_qty / line_kit_qty
            )
            if product.is_kit:
                for component in unavailable_component_qties:
                    unavailable_component_qties[component] += (
                        component_qties.get(component, 0)
                        * line.product_uom_qty
                        / line_kit_qty
                    )

        if product.is_kit:
            max_free_kit_qty = qty_free = product.sudo().qty_free
            for (
                component,
                unavailable_component_qty,
            ) in unavailable_component_qties.items():
                max_free_kit_qty = min(
                    max_free_kit_qty,
                    (component.qty_free - unavailable_component_qty)
                    // qty_per_kit[component],
                )
            unavailable_qty += qty_free - max_free_kit_qty
        return unavailable_qty
