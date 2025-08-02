from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    product_packaging_qty = fields.Float(string="Packaging Quantity", store=True)
    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', domain="[('product_id', '=', product_id)]")

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        """Recalculate Packaging Quantity based on Product Quantity."""
        if self.product_packaging_id and self.product_packaging_id.qty > 0:
            self.product_packaging_qty = self.product_uom_qty / self.product_packaging_id.qty
        else:
            self.product_packaging_qty = 0

    @api.onchange('product_packaging_qty')
    def _onchange_product_packaging_qty(self):
        """Recalculate Product Quantity based on Packaging Quantity."""
        if self.product_packaging_id and self.product_packaging_id.qty > 0:
            self.product_uom_qty = self.product_packaging_qty * self.product_packaging_id.qty
        else:
            self.product_uom_qty = 0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Ensure proper packaging selection based on Product."""
        super(StockMove, self)._onchange_product_id()
        if self.product_id:
            self.product_packaging_id = self.product_id.packaging_ids[:1] if self.product_id.packaging_ids else False
            self._compute_qtys()

    def _compute_qtys(self):
        """Compute quantities for product and packaging."""
        if self.product_packaging_id and self.product_packaging_id.qty > 0:
            self.product_packaging_qty = self.product_uom_qty / self.product_packaging_id.qty
            self.product_uom_qty = self.product_packaging_qty * self.product_packaging_id.qty
        else:
            self.product_packaging_qty = 0
            self.product_uom_qty = 0
