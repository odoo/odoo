# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_kit_value_per_unit(self):
        if self.env.context.get('component_valuation'):
            return 0
        order_line = self.sale_line_id
        if order_line and all(move.sale_line_id == order_line for move in self) and any(move.product_id != order_line.product_id for move in self):
            product = order_line.product_id.with_company(order_line.company_id)
            bom = product.env['mrp.bom']._bom_find(product, company_id=self.company_id.id, bom_type='phantom')[product]
            if bom:
                return self._get_kit_price_unit(product, bom, order_line.product_uom_qty)
        return 0

    def _get_price_unit(self):
        kit_unit_price = self._get_kit_value_per_unit()
        if kit_unit_price:
            return kit_unit_price
        return super()._get_price_unit()

    def _get_price_unit_dropshipped(self):
        """ Overridden to handle Kit dropship products correctly. """
        kit_unit_price = self._get_kit_value_per_unit()
        if kit_unit_price:
            return kit_unit_price
        return super()._get_price_unit_dropshipped()

    def _get_source_document(self):
        return self.production_id or self.raw_material_production_id or super()._get_source_document()

    def _get_cogs_price_unit(self, quantity=0):
        "Override needed for when the product is a kit"
        price_unit = super()._get_cogs_price_unit()

        so_line = self.sale_line_id and self.sale_line_id[-1] or False
        if so_line:
            # We give preference to the bom in the stock moves for the sale order lines
            # If there are changes in BOMs between the stock moves creation and the
            # invoice validation a wrong price will be taken
            boms = so_line.move_ids.filtered(lambda m: m.state != 'cancel').mapped('bom_line_id.bom_id').filtered(lambda b: b.type == 'phantom')
            if boms:
                bom = boms.filtered(lambda b: b.product_id == so_line.product_id or b.product_tmpl_id == so_line.product_id.product_tmpl_id)
                if not bom:
                    # In the case where the product has no direct component in its bom, it won't be present in the stock moves boms.
                    # We then take the first bom of the product.
                    bom = self.env['mrp.bom']._bom_find(products=so_line.product_id, company_id=so_line.company_id.id, bom_type='phantom')[so_line.product_id]
                    if not bom:
                        return price_unit

                components_qty = so_line._get_bom_component_qty(bom)
                storable_components = self.env['product.product'].search([('id', 'in', list(components_qty.keys())), ('is_storable', '=', True)])

                average_price_unit = 0
                for product in storable_components:
                    prod_move = self.filtered(lambda m: m.product_id == product)
                    product = product.with_company(self.company_id)
                    average_price_unit += super(StockMove, prod_move)._get_cogs_price_unit() * components_qty[product.id]['qty']
                price_unit = average_price_unit / bom.product_qty or price_unit
        return price_unit
