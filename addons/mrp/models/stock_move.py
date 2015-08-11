# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError
from openerp.tools import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    production_id = fields.Many2one('mrp.production', string='Production Order for Produced Products', index=True, copy=False)
    raw_material_production_id = fields.Many2one('mrp.production', string='Production Order for Raw Materials', index=True)
    consumed_for_id = fields.Many2one('stock.move', string='Consumed for', help='Technical field used to make the traceability of produced products', oldname='consumed_for')

    @api.model
    def check_tracking(self, move, lot_id):
        super(StockMove, self).check_tracking(move, lot_id)
        if move.raw_material_production_id and move.product_id.tracking != 'none' and move.location_dest_id.usage == 'production' and move.raw_material_production_id.product_id.tracking != 'none' and not move.consumed_for_id:
            raise UserError(_("Because the product %s requires it, you must assign a serial number to your raw material %s to proceed further in your production. Please use the 'Produce' button to do so.") % (move.raw_material_production_id.product_id.name, move.product_id.name))

    def _action_explode(self):
        """ Explodes pickings.
        :return: True
        """
        ProductProduct = self.env['product.product']
        ProcurementOrder = self.env['procurement.order']
        to_explode_again_ids = self - self
        properties = self.env.context.get('properties') or None
        bom_point = self.env['mrp.bom'].sudo()._bom_find(product=self.product_id, properties=properties)
        if bom_point and bom_point.bom_type == 'phantom':
            processed_ids = self - self
            factor = self.product_uom.sudo()._compute_qty(self.product_uom_qty, bom_point.product_uom_id.id) / bom_point.product_qty
            res = bom_point.sudo().explode(self.product_id, factor, properties)

            for line in res[0]:
                product = ProductProduct.browse(line['product_id'])
                if product.type in ['product', 'consu']:
                    valdef = {
                        'picking_id': self.picking_id.id if self.picking_id else False,
                        'product_id': line['product_id'],
                        'product_uom': line['product_uom_id'],
                        'product_uom_qty': line['product_qty'],
                        'state': 'draft',  # will be confirmed below
                        'name': line['name'],
                        'procurement_id': self.procurement_id.id,
                        'split_from': self.id,  # Needed in order to keep sale connection, but will be removed by unlink
                    }
                    mid = self.copy(default=valdef)
                    to_explode_again_ids = to_explode_again_ids | mid
                else:
                    if product.type in ('consu', 'product'):
                        valdef = {
                            'name': self.rule_id and self.rule_id.name or "/",
                            'origin': self.origin,
                            'company_id': self.company_id and self.company_id.id or False,
                            'date_planned': self.date,
                            'product_id': line['product_id'],
                            'product_qty': line['product_qty'],
                            'product_uom_id': line['product_uom_id'],
                            'group_id': self.group_id.id,
                            'priority': self.priority,
                            'partner_dest_id': self.partner_id.id,
                        }
                        if self.procurement_id:
                            procurement = self.procurement_id.copy(default=valdef)
                        else:
                            procurement = ProcurementOrder.create(valdef)
                        procurement.run()  # could be omitted

            # check if new moves needs to be exploded
            if to_explode_again_ids:
                for new_move in to_explode_again_ids:
                    processed_ids = processed_ids | new_move._action_explode()

            if not self.split_from and self.procurement_id:
                # Check if procurements have been made to wait for
                moves = self.procurement_id.move_ids
                if len(moves) == 1:
                    self.procurement_id.write({'state': 'done'})

            if processed_ids and self.state == 'assigned':
                # Set the state of resulting moves according to 'assigned' as the original move is assigned
                processed_ids.write({'state': 'assigned'})

            # delete the move with original product which is not relevant anymore
            self.sudo().unlink()
            # return list of newly created move
            return processed_ids

        return self

    @api.multi
    def action_confirm(self):
        moves = self - self
        for move in self:
            # in order to explode a move, we must have a picking_type_id on that move because otherwise the move
            # won't be assigned to a picking and it would be weird to explode a move into several if they aren't
            # all grouped in the same picking.
            if move.picking_type_id:
                moves = moves | move._action_explode()
            else:
                moves = moves | move

        # we go further with the list of ids potentially changed by action_explode
        return super(StockMove, moves).action_confirm()

    def action_consume(self, product_qty, location_id=False, restrict_lot_id=False, restrict_partner_id=False, consumed_for_id=False):
        """ Consumed product with specific quantity from specific source location.
        :param product_qty: Consumed/produced product quantity (= in quantity of UoM of product)
        :param location_id: Source location
        :param restrict_lot_id: optionnal parameter that allows to restrict the choice of quants on this specific lot
        :param restrict_partner_id: optionnal parameter that allows to restrict the choice of quants to this specific partner
        :param consumed_for_id: optionnal parameter given to this function to make the link between raw material consumed and produced product, for a better traceability
        :return: New lines created if not everything was consumed for this line
        """
        res = self - self  # creates empty recordset

        if product_qty <= 0:
            raise UserError(_('Please provide proper quantity.'))
        # because of the action_confirm that can create extra moves in case of phantom bom, we need to make 2 loops
        ids2 = []
        for move in self:
            if move.state == 'draft':
                ids2.extend(move.action_confirm())
            else:
                ids2.append(move.id)

        prod_orders = self.env['mrp.production']
        for move in self.browse(ids2):
            prod_orders = prod_orders | move.raw_material_production_id or move.production_id
            move_qty = move.product_qty
            if move_qty <= 0:
                raise UserError(_('Cannot consume a move with negative or zero quantity.'))
            quantity_rest = move_qty - product_qty
            # Compare with numbers of move uom as we want to avoid a split with 0 qty
            quantity_rest_uom = move.product_uom_qty - self.env['product.uom']._compute_qty_obj(move.product_id.uom_id, product_qty, move.product_uom)
            if float_compare(quantity_rest_uom, 0, precision_rounding=move.product_uom.rounding) != 0:
                new_mov = self.browse(self.split(move, quantity_rest))
                if move.production_id:
                    new_mov.write({'production_id': move.production_id.id})
                res = res | new_mov
            vals = {'restrict_lot_id': restrict_lot_id,
                    'restrict_partner_id': restrict_partner_id,
                    'consumed_for_id': consumed_for_id}
            if location_id:
                vals.update({'location_id': location_id})
            move.write(vals)
        # Original moves will be the quantities consumed, so they need to be done
        self.browse(ids2).action_done()
        if res:
            res.action_assign()
        if prod_orders:
            prod_orders.signal_workflow('button_produce')
        return res

    @api.multi
    def action_scrap(self, product_qty, location_id, restrict_lot_id=False, restrict_partner_id=False):
        """ Move the scrap/damaged product into scrap location
        :param product_qty: Scraped product quantity
        :param location_id: Scrap location
        :return: Scraped lines
        """
        MrpProduction = self.env['mrp.production']
        res = self - self
        for move in self:
            new_moves = super(StockMove, move).action_scrap(product_qty, location_id, restrict_lot_id=restrict_lot_id, restrict_partner_id=restrict_partner_id)
            # If we are not scrapping our whole move, tracking and lot references must not be removed
            production_ids = MrpProduction.search([('move_line_ids', 'in', [move.id])])
            for prod_id in production_ids:
                prod_id.signal_workflow('button_produce')
            if move.production_id.id:
                new_moves.write({'production_id': move.production_id.id})
            res = res | new_moves
        return res

    @api.multi
    def write(self, vals):
        res = super(StockMove, self).write(vals)
        from openerp import workflow
        if vals.get('state') == 'assigned':
            orders = self.filtered(lambda x: x.raw_material_production_id and x.raw_material_production_id.state == 'confirmed').raw_material_production_id
            for order in orders:
                if order.test_ready():
                    workflow.trg_validate(self.env.uid, 'mrp.production', order.id, 'moves_ready', self.env.cr)
        return res
