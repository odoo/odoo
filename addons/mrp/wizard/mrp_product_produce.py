# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
import openerp.addons.decimal_precision as dp


class MrpProductProduceLine(models.TransientModel):
    _name="mrp.product.produce.line"
    _description = "Product Produce Consume lines"

    product_id = fields.Many2one('product.product', string='Product')
    product_qty = fields.Float(string='Quantity (in default UoM)', digits_compute=dp.get_precision('Product Unit of Measure'))
    lot_id = fields.Many2one('stock.production.lot', string='Lot')
    produce_id = fields.Many2one('mrp.product.produce', string='Produce')


class MrpProductProduce(models.TransientModel):
    _name = "mrp.product.produce"
    _description = "Product Produce"

    @api.model
    def _get_product_qty(self):
        """ To obtain product quantity
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param context: A standard dictionary
        @return: Quantity
        """
        production = self.env['mrp.production'].browse(self._context['active_id'])
        done = 0.0
        for move in production.move_created_ids2:
            if move.product_id == production.product_id:
                if not move.scrapped:
                    done += move.product_uom_qty # As uom of produced products and production order should correspond
        return production.product_qty - done

    @api.model
    def _get_product_id(self):
        """ To obtain product id
        @return: id
        """
        production = False
        if self._context and self._context.get("active_id"):
            production = self.env['mrp.production'].browse(self._context['active_id'])
        return production and production.product_id.id or False

    @api.model
    def _get_track(self):
        production = self._get_product_id()
        return production and self.env['product.product'].browse(production).tracking or False

    product_id = fields.Many2one('product.product', default=_get_product_id)
    product_qty = fields.Float(string='Select Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, default=_get_product_qty)
    mode = fields.Selection([('consume_produce', 'Consume & Produce'),
                              ('consume', 'Consume Only')], string='Mode', required=True, default='consume_produce',
                              help="'Consume only' mode will only consume the products with the quantity selected.\n"
                                    "'Consume & Produce' mode will consume as well as produce the products with the quantity selected "
                                    "and it will finish the production order when total ordered quantities are produced.")
    lot_id = fields.Many2one('stock.production.lot', string='Lot')  # Should only be visible when it is consume and produce mode
    consume_lines = fields.One2many('mrp.product.produce.line', 'produce_id', string='Products Consumed')
    tracking = fields.Selection(related='product_id.tracking', selection=[('serial', 'By Unique Serial Number'), ('lot', 'By Lots'), ('none', 'No Tracking')], default=_get_track)

    @api.multi
    def on_change_qty(self, product_qty, consume_lines):
        """ 
            When changing the quantity of products to be produced it will 
            recalculate the number of raw materials needed according
            to the scheduled products and the already consumed/produced products
            It will return the consume lines needed for the products to be produced
            which the user can still adapt
        """
        production = self.env['mrp.production'].browse(self._context['active_id'])
        consume_lines = []
        new_consume_lines = []
        if product_qty > 0.0:
            product_uom_qty = self.env['product.uom']._compute_qty(production.product_uom_id.id, product_qty, production.product_id.uom_id.id)
            consume_lines = self.env['mrp.production']._calculate_qty(production, product_qty=product_uom_qty)

        for consume in consume_lines:
            new_consume_lines.append([0, False, consume])
        return {'value': {'consume_lines': new_consume_lines}}

    @api.multi
    def do_produce(self):
        production_id = self._context.get('active_id', False)
        assert production_id, "Production Id should be specified in context as a Active ID."
        self.env['mrp.production'].action_produce(production_id, self.product_qty, self.mode, self)
        return {}
