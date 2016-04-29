# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class ProductProductLine(models.TransientModel):
    _name = "mrp.product.produce.line"
    _description = "Product Produce Consume lines"

    product_id = fields.Many2one('product.product', string='Product')
    product_qty = fields.Float('Quantity (in default UoM)', digits_compute=dp.get_precision('Product Unit of Measure'))
    lot_id = fields.Many2one('stock.production.lot', string='Lot')
    produce_id = fields.Many2one('mrp.product.produce', string="Produce")


class ProductProduce(models.TransientModel):
    _name = "mrp.product.produce"
    _description = "Product Produce"

    def _get_default_product_id(self):
        if self._context.get('active_id'):
            production = self.env['mrp.production'].browse(self._context['active_id'])
            return production.product_id.id
        return False

    def _get_default_product_qty(self):
        production = self.env['mrp.production'].browse(self._context['active_id'])
        done = 0.0
        for move in production.move_created_ids2.filtered(lambda move: not move.scrapped and move.product_id == production.product_id):
            done += move.product_uom_qty  # As uom of produced products and production order should correspond
        return production.product_qty - done

    def _get_default_tracking(self):
        production = self.env['mrp.production'].browse(self._context['active_id'])
        return production.product_id.tracking

    product_id = fields.Many2one(
        'product.product', 'Product',
        default=_get_default_product_id)
    product_qty = fields.Float(
        'Select Quantity', default=_get_default_product_qty,
        digits_compute=dp.get_precision('Product Unit of Measure'), required=True)
    mode = fields.Selection([
        ('consume_produce', 'Consume & Produce'),
        ('consume', 'Consume Only')], 'Mode',
        default='consume_produce', required=True,
        help="'Consume only' mode will only consume the products with the quantity selected.\n"
             "'Consume & Produce' mode will consume as well as produce the products with the quantity selected "
             "and it will finish the production order when total ordered quantities are produced.")
    lot_id = fields.Many2one('stock.production.lot', 'Lot')  # Should only be visible when it is consume and produce mode
    consume_lines = fields.One2many('mrp.product.produce.line', 'produce_id', 'Products Consumed')
    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')],
        related='product_id.tracking',
        default=_get_default_tracking)

    @api.multi
    @api.onchange('product_qty')
    def on_change_qty(self):
        """
            When changing the quantity of products to be produced it will
            recalculate the number of raw materials needed according
            to the scheduled products and the already consumed/produced products
            It will return the consume lines needed for the products to be produced
            which the user can still adapt
        """
        production = self.env['mrp.production'].browse(self._context['active_id'])
        Production = self.env["mrp.production"]
        UoM = self.env["product.uom"]
        consume_lines = []
        new_consume_lines = []
        if self.product_qty > 0.0:
            product_uom_qty = UoM._compute_qty_obj(production.product_uom, self.product_qty, production.product_id.uom_id)
            consume_lines = Production._calculate_qty(production, product_qty=product_uom_qty)

        for consume in consume_lines:
            new_consume_lines.append([0, False, consume])
        self.consume_lines = new_consume_lines

    @api.multi
    def do_produce(self):
        # TDE FIXME: put prod in field
        production_id = self.env.context['active_id']
        for wizard in self:
            self.env['mrp.production'].browse(production_id).action_produce(wizard.product_qty, wizard.mode, wizard)
        return {}
