# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models
from odoo.tools import float_is_zero


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_unavailable_quantity_from_kits(self, product):
        """
        If any line of the order refers to a kit product, the availability of the product
        might be impacted (if the product is a kit or a component of one).

        This method computes the quantity that becomes unavailable for the product because
        of the order lines that do not refer to it directly.

        :param ProductProduct product: the product for which the unavailability is computed.
        """
        self.ensure_one()
        unavailable_qty = 0
        if product.is_kits:
            # Explode the kit to fetch the set of relevant components to track.
            kit_bom = self.env['mrp.bom'].sudo()._bom_find(product, company_id=self.company_id.id, bom_type='phantom')[product]
            _, bom_sub_lines = kit_bom.explode(product, quantity=1.0)
            unavailable_component_qties = {}
            qty_per_kit = defaultdict(float)
            for bom_line, bom_line_data in bom_sub_lines:
                if not bom_line.product_id.is_storable:
                    # Relevant only for storable components.
                    continue
                if float_is_zero(bom_line_data['qty'], precision_rounding=bom_line.product_uom_id.rounding):
                    # As BoMs allow components with a quantity of 0 (i.e., optional components), we
                    # skip those to avoid a division by zero.
                    continue
                component = bom_line.product_id
                unavailable_component_qties[component] = sum(self.order_line.filtered(lambda sol: sol.product_id == component).mapped('product_uom_qty'))
                uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                qty_per_kit[component] += bom_line.product_uom_id._compute_quantity(uom_qty_per_kit / kit_bom.product_qty, component.uom_id, round=False)

        for line in self.order_line:
            if not line.product_id.is_kits or line.product_id == product:
                continue
            # Other kit lines might influence the availability of the product.
            line_kit_bom = self.env['mrp.bom'].sudo()._bom_find(line.product_id, company_id=self.company_id.id, bom_type='phantom')[line.product_id]
            component_qties = line._get_bom_component_qty(line_kit_bom)
            unavailable_qty += component_qties.get(product.id, {}).get('qty', 0) * line.product_uom_qty / line_kit_bom.product_qty
            if product.is_kits:
                # If the product is a kit, the availability of its components can be influenced by other kits.
                for component, _ in unavailable_component_qties.items():
                    unavailable_component_qties[component] += component_qties.get(component.id, {}).get('qty', 0) * line.product_uom_qty / line_kit_bom.product_qty

        if product.is_kits:
            # If the product is a kit, recompute availability based on the availability of its components.
            max_free_kit_qty = free_qty = product.sudo().free_qty
            for component, unavailable_component_qty in unavailable_component_qties.items():
                max_free_kit_qty = min(max_free_kit_qty, (component.free_qty - unavailable_component_qty) // qty_per_kit[component])
            unavailable_qty += free_qty - max_free_kit_qty
        return unavailable_qty
