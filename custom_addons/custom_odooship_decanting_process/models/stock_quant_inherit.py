from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    product_packaging_id = fields.Many2one(
        'product.packaging',
        string='Product Packaging',
        domain="[('product_id', '=', product_id)]",
        check_company=True
    )

    product_packaging_qty = fields.Float(
        string='Packaging Quantity',
        compute='_compute_product_packaging_qty',
        inverse='_inverse_product_packaging_qty',
        store=True
    )

    inventory_packaging_quantity = fields.Float(
        string='Counted Packaging Quantity',
        compute='_compute_inventory_packaging_quantity',
        inverse='_inverse_inventory_packaging_quantity',
        store=True
    )

    @api.depends('quantity', 'product_packaging_id')
    def _compute_product_packaging_qty(self):
        for quant in self:
            if quant.product_packaging_id and quant.product_packaging_id.qty:
                quant.product_packaging_qty = quant.quantity / quant.product_packaging_id.qty
            else:
                quant.product_packaging_qty = 0.0

    def _inverse_product_packaging_qty(self):
        for quant in self:
            if quant.product_packaging_id and quant.product_packaging_id.qty:
                quant.quantity = quant.product_packaging_qty * quant.product_packaging_id.qty
            else:
                quant.quantity = quant.quantity or 0.0

    @api.depends('inventory_quantity', 'product_packaging_id')
    def _compute_inventory_packaging_quantity(self):
        for quant in self:
            if quant.product_packaging_id and quant.product_packaging_id.qty:
                quant.inventory_packaging_quantity = quant.inventory_quantity / quant.product_packaging_id.qty
            else:
                quant.inventory_packaging_quantity = 0.0

    def _inverse_inventory_packaging_quantity(self):
        for quant in self:
            if quant.product_packaging_id and quant.product_packaging_id.qty:
                quant.inventory_quantity = quant.inventory_packaging_quantity * quant.product_packaging_id.qty
            else:
                quant.inventory_quantity = quant.inventory_quantity or 0.0

    def action_apply_inventory(self):
        for quant in self:
            packaging = quant.product_packaging_id
            if packaging and packaging.qty:
                # If packaging and qty defined, calculate inventory qty accordingly
                quant.inventory_quantity = quant.inventory_packaging_quantity * packaging.qty
                quant.product_packaging_qty = quant.inventory_packaging_quantity

        # Now call the base method to apply the inventory quantity to stock
        super(StockQuantInherit, self).action_apply_inventory()
        return None

