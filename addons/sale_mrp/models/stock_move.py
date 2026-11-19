# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends('bom_line_id')
    def _compute_packaging_uom_id(self):
        super()._compute_packaging_uom_id()
        for move in self:
            if move.bom_line_id and move.bom_line_id.bom_id.type == 'phantom':
                move.packaging_uom_id = move.uom_id

<<<<<<< c25a8e8786c13b2a7aee58645e37cb27d32a51c5
||||||| 08b2401887196f8a0e10e0166a1b86a5fd6400b3
    def _get_kit_value_per_unit(self):
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

=======
    def _get_price_unit_delivery(self):
        """ Overridden to price a kit as the sum of its components, each from its own moves """
        order_line = self.sale_line_id
        if order_line and all(move.sale_line_id == order_line for move in self) and any(move.product_id != order_line.product_id for move in self):
            product = order_line.product_id
            bom = self.bom_line_id.bom_id.filtered(lambda b: b.type == 'phantom' and b.product_tmpl_id == product.product_tmpl_id)[:1]
            if not bom:
                bom = self.env['mrp.bom']._bom_find(product, company_id=order_line.company_id.id, bom_type='phantom')[product]
            if bom:
                components_qty = order_line._get_bom_component_qty(bom)
                price_unit = 0
                for component, component_moves in self.grouped('product_id').items():
                    if component.id in components_qty:
                        price_unit += super(StockMove, component_moves)._get_price_unit_delivery() * components_qty[component.id]['qty']
                return price_unit / bom.product_qty
        return super()._get_price_unit_delivery()

>>>>>>> 7d1879a7ebd67f5370be0053eb054027d22c9e93
    def _get_source_document(self):
        return self.production_id or self.raw_material_production_id or super()._get_source_document()

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        distribution = self.raw_material_production_id.sale_line_id.analytic_distribution
        if distribution and not res.get('analytic_distribution'):
            res['analytic_distribution'] = distribution
        return res
