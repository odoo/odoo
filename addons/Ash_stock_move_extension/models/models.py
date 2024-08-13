from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    product_packaging_qty = fields.Float(string="Packaging Quantity", compute='_compute_product_packaging_qty', store=True)
    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', domain="[('product_id', '=', product_id)]")

    @api.depends('product_uom_qty', 'product_packaging_id.qty')
    def _compute_product_packaging_qty(self):
        for move in self:
            if move.product_packaging_id and move.product_packaging_id.qty > 0:
                move.product_packaging_qty = move.product_uom_qty / move.product_packaging_id.qty
            else:
                move.product_packaging_qty = 0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        super(StockMove, self)._onchange_product_id()
        if self.product_id:
            self.product_packaging_id = self.product_id.packaging_ids[:1] if self.product_id.packaging_ids else False
            if self.product_packaging_id and self.product_packaging_id.qty > 0:
                self.product_packaging_qty = self.product_uom_qty / self.product_packaging_id.qty
            else:
                self.product_packaging_qty = 0
