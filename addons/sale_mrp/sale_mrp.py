# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
from openerp.tools import float_compare


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    sale_name = fields.Char(compute='_compute_sale_name_sale_ref', string='Sale Name', help='Indicate the name of sales order.')
    sale_ref = fields.Char(compute='_compute_sale_name_sale_ref', string='Sale Reference', help='Indicate the Customer Reference from sales order.')

    @api.multi
    def _compute_sale_name_sale_ref(self):
        def get_parent_move(move):
            if move.move_dest_id:
                return get_parent_move(move.move_dest_id)
            return move
        for production in self:
            if production.move_prod_id:
                move = get_parent_move(production.move_prod_id)
                production.sale_name = move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.name or False
                production.sale_ref = move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.client_order_ref or False


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    property_ids = fields.Many2many('mrp.property', 'sale_order_line_property_rel', 'order_id', 'property_id', 'Properties', readonly=True, states={'draft': [('readonly', False)]})

    @api.multi
    def _get_delivered_qty(self):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # In the case of a kit, we need to check if all components are shipped. We use a all or
        # nothing policy. A product can have several BoMs, we don't know which one was used when the
        # delivery was created.
        bom_delivered = {}
        bom_id = self.env['mrp.bom']._bom_find(product_id=self.product_id.id, properties=self.property_ids.ids)
        bom = self.env['mrp.bom'].browse(bom_id)
        if bom and bom.type == 'phantom':
            bom_delivered[bom.id] = False
            product_uom_qty_bom = self.env['product.uom']._compute_qty_obj(self.product_uom, self.product_uom_qty, bom.product_uom)
            bom_exploded = self.env['mrp.bom']._bom_explode(bom, self.product_id, product_uom_qty_bom)[0]
            for bom_line in bom_exploded:
                qty = 0.0
                for move in self.procurement_ids.mapped('move_ids'):
                    if move.state == 'done' and move.product_id.id == bom_line.get('product_id', False):
                        qty += self.env['product.uom']._compute_qty(move.product_uom.id, move.product_uom_qty, bom_line['product_uom'])
                if float_compare(qty, bom_line['product_qty'], precision_digits=precision) < 0:
                    bom_delivered[bom.id] = False
                    break
                else:
                    bom_delivered[bom.id] = True
        if bom_delivered and any(bom_delivered.values()):
            return self.product_uom_qty
        elif bom_delivered:
            return 0.0
        return super(SaleOrderLine, self)._get_delivered_qty()

    @api.multi
    def _get_bom_component_qty(self, bom):
        product_uom_qty_bom = self.env['product.uom']._compute_qty_obj(self.product_uom, self.product_uom_qty, bom.product_uom)
        bom_exploded = self.env['mrp.bom']._bom_explode(bom, self.product_id, product_uom_qty_bom)[0]
        components = {}
        for bom_line in bom_exploded:
            product = bom_line['product_id']
            uom = bom_line['product_uom']
            qty = bom_line['product_qty']
            if components.get(product, False):
                if uom != components[product]['uom']:
                    from_uom_id = uom
                    to_uom_id = components[product]['uom']
                    qty = self.env['product.uom']._compute_qty(from_uom_id, qty, to_uom_id=to_uom_id)
                components[product]['qty'] += qty
            else:
                # To be in the uom reference of the product
                to_uom = self.env['product.product'].browse([product])[0].uom_id.id
                if uom != to_uom:
                    qty = self.env['product.uom']._compute_qty(uom, qty, to_uom_id=to_uom)
                components[product] = {'qty': qty, 'uom': to_uom}
        return components



    @api.multi
    def _prepare_order_line_procurement(self, group_id=False):
        vals = super(SaleOrderLine, self)._prepare_order_line_procurement(group_id=group_id)
        vals['property_ids'] = [(6, 0, self.property_ids.ids)]
        return vals


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def _prepare_procurement_from_move(self, move):
        res = super(StockMove, self)._prepare_procurement_from_move(move)
        if res and move.procurement_id and move.procurement_id.property_ids:
            res['property_ids'] = [(6, 0, move.procurement_id.property_ids.ids)]
        return res

    @api.model
    def _action_explode(self, move):
        """ Explodes pickings.
        @param move: Stock moves
        @return: True
        """
        property_ids = move.procurement_id.sale_line_id.property_ids.ids
        return super(StockMove, self.with_context(property_ids=property_ids))._action_explode(move)

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def _get_anglo_saxon_price_unit(self):
        price_unit = super(AccountInvoiceLine, self)._get_anglo_saxon_price_unit()
        # in case of anglo saxon with a product configured as invoiced based on delivery, with perpetual
        # valuation and real price costing method, we must find the real price for the cost of good sold
        uom_obj = self.env['product.uom']
        if self.product_id.invoice_policy == "delivery":
            for s_line in self.sale_line_ids:
                # qtys already invoiced
                qty_done = sum([uom_obj._compute_qty_obj(x.uom_id, x.quantity, x.product_id.uom_id) for x in s_line.invoice_lines if x.invoice_id.state in ('open', 'paid')])
                quantity = uom_obj._compute_qty_obj(self.uom_id, self.quantity, self.product_id.uom_id)
                # Put moves in fixed order by date executed
                moves = s_line.mapped('procurement_ids.move_ids').sorted(lambda x: x.date)
                # Go through all the moves and do nothing until you get to qty_done
                # Beyond qty_done we need to calculate the average of the price_unit
                # on the moves we encounter.
                bom = s_line.product_id.product_tmpl_id.bom_ids and s_line.product_id.product_tmpl_id.bom_ids[0]
                if bom.type == 'phantom':
                    average_price_unit = 0
                    components = s_line._get_bom_component_qty(bom)
                    for product_id in components.keys():
                        factor = components[product_id]['qty']
                        prod_moves = [m for m in moves if m.product_id.id == product_id]
                        prod_qty_done = factor * qty_done
                        prod_quantity = factor * quantity
                        average_price_unit += self._compute_average_price(prod_qty_done, prod_quantity, prod_moves)
                    price_unit = average_price_unit or price_unit
                    price_unit = self.product_id.uom_id._compute_price(self.product_id.uom_id.id, price_unit, to_uom_id=self.uom_id.id)
        return price_unit
