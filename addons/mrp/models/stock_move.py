# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError
from openerp.tools import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    production_id = fields.Many2one('mrp.production', string='Production Order for Produced Products', select=True, copy=False)
    raw_material_production_id = fields.Many2one('mrp.production', string='Production Order for Raw Materials', select=True)
    consumed_for_id = fields.Many2one('stock.move', string='Consumed for', help='Technical field used to make the traceability of produced products', oldname='consumed_for')

    @api.model
    def check_tracking(self, move, lot_id):
        super(StockMove, self).check_tracking(move, lot_id)
        if move.raw_material_production_id and move.product_id.tracking!='none' and move.location_dest_id.usage == 'production' and move.raw_material_production_id.product_id.tracking != 'none' and not move.consumed_for_id:
            raise UserError(_("Because the product %s requires it, you must assign a serial number to your raw material %s to proceed further in your production. Please use the 'Produce' button to do so.") % (move.raw_material_production_id.product_id.name, move.product_id.name))

    @api.model
    def _action_explode(self, move):
        """ Explodes pickings.
        @param move: Stock moves
        @return: True
        """
        MrpBom = self.env['mrp.bom']
        StockMove = self.env['stock.move']
        ProductProduct = self.env['product.product']
        ProcurementOrder = self.env['procurement.order']
        to_explode_again_ids = []
        property_ids = self.env.context.get('property_ids') or []
        bis = MrpBom.sudo()._bom_find(product_id=move.product_id.id, properties=property_ids)
        bom_point = MrpBom.sudo().browse(bis)
        if bis and bom_point.bom_type == 'phantom':
            processed_ids = []
            factor = self.env['product.uom'].sudo()._compute_qty(move.product_uom.id, move.product_uom_qty, bom_point.product_uom_id.id) / bom_point.product_qty
            res = MrpBom.sudo()._bom_explode(bom_point, move.product_id, factor, property_ids)

            for line in res[0]:
                product = ProductProduct.browse(line['product_id'])
                if product.type != 'service':
                    valdef = {
                        'picking_id': move.picking_id.id if move.picking_id else False,
                        'product_id': line['product_id'],
                        'product_uom': line['product_uom_id'],
                        'product_uom_qty': line['product_qty'],
                        'product_uos': line['product_uos_id'],
                        'product_uos_qty': line['product_uos_qty'],
                        'state': 'draft',  #will be confirmed below
                        'name': line['name'],
                        'procurement_id': move.procurement_id.id,
                        'split_from': move.id, #Needed in order to keep sale connection, but will be removed by unlink
                    }
                    mid = StockMove.browse(move.id).copy(default=valdef)
                    to_explode_again_ids.append(mid.id)
                else:
                    if ProductProduct.need_procurement():
                        valdef = {
                            'name': move.rule_id and move.rule_id.name or "/",
                            'origin': move.origin,
                            'company_id': move.company_id and move.company_id.id or False,
                            'date_planned': move.date,
                            'product_id': line['product_id'],
                            'product_qty': line['product_qty'],
                            'product_uom_id': line['product_uom_id'],
                            'product_uos_qty': line['product_uos_qty'],
                            'product_uos_id': line['product_uos_id'],
                            'group_id': move.group_id.id,
                            'priority': move.priority,
                            'partner_dest_id': move.partner_id.id,
                        }
                        if move.procurement_id:
                            procurement = ProcurementOrder.browse(move.procurement_id.id).copy(default=valdef)
                        else:
                            procurement = ProcurementOrder.create(valdef)
                        ProcurementOrder.run([procurement])  # could be omitted

            #check if new moves needs to be exploded
            if to_explode_again_ids:
                for new_move in self.browse(to_explode_again_ids):
                    processed_ids.extend(self._action_explode(new_move))

            if not move.split_from and move.procurement_id:
                # Check if procurements have been made to wait for
                moves = move.procurement_id.move_ids
                if len(moves) == 1:
                    move.procurement_id.write({'state': 'done'})

            if processed_ids and move.state == 'assigned':
                # Set the state of resulting moves according to 'assigned' as the original move is assigned
                StockMove.browse(list(set(processed_ids) - set([move.id]))).write({'state': 'assigned'})

            #delete the move with original product which is not relevant anymore
            StockMove.browse(move.id).sudo().unlink()
            #return list of newly created move
            return processed_ids

        return [move.id]

    @api.multi
    def action_confirm(self):
        move_ids = []
        for move in self:
            #in order to explode a move, we must have a picking_type_id on that move because otherwise the move
            #won't be assigned to a picking and it would be weird to explode a move into several if they aren't
            #all grouped in the same picking.
            if move.picking_type_id:
                move_ids.extend(self.env['stock.move']._action_explode(move))
            else:
                move_ids.append(move.id)

        #we go further with the list of ids potentially changed by action_explode
        return super(StockMove, self.browse(move_ids)).action_confirm()

    @api.model
    def action_consume(self, product_qty, location_id=False, restrict_lot_id=False, restrict_partner_id=False, consumed_for_id=False):
        """ Consumed product with specific quantity from specific source location.
        @param product_qty: Consumed/produced product quantity (= in quantity of UoM of product)
        @param location_id: Source location
        @param restrict_lot_id: optionnal parameter that allows to restrict the choice of quants on this specific lot
        @param restrict_partner_id: optionnal parameter that allows to restrict the choice of quants to this specific partner
        @param consumed_for_id: optionnal parameter given to this function to make the link between raw material consumed and produced product, for a better traceability
        @return: New lines created if not everything was consumed for this line
        """
        res = []

        if product_qty <= 0:
            raise UserError(_('Please provide proper quantity.'))
        #because of the action_confirm that can create extra moves in case of phantom bom, we need to make 2 loops
        ids2 = []
        for move in self:
            if move.state == 'draft':
                ids2.extend(self.action_confirm())
            else:
                ids2.append(move.id)

        prod_orders = set()
        for move in self.browse(ids2):
            prod_orders.add(move.raw_material_production_id.id or move.production_id.id)
            move_qty = move.product_qty
            if move_qty <= 0:
                raise UserError(_('Cannot consume a move with negative or zero quantity.'))
            quantity_rest = move_qty - product_qty
            # Compare with numbers of move uom as we want to avoid a split with 0 qty
            quantity_rest_uom = move.product_uom_qty - self.env['product.uom']._compute_qty_obj(move.product_id.uom_id, product_qty, move.product_uom)
            if float_compare(quantity_rest_uom, 0, precision_rounding=move.product_uom.rounding) != 0:
                new_mov = self.split(move, quantity_rest)
                if move.production_id:
                    self.browse(new_mov).write({'production_id': move.production_id.id})
                res.append(new_mov)
            vals = {'restrict_lot_id': restrict_lot_id,
                    'restrict_partner_id': restrict_partner_id,
                    'consumed_for_id': consumed_for_id}
            if location_id:
                vals.update({'location_id': location_id})
            move.write(vals)
        # Original moves will be the quantities consumed, so they need to be done
        self.action_done()
        if res:
            self.action_assign()
        if prod_orders:
            self.env['mrp.production'].browse(prod_orders).signal_workflow('button_produce')
        return res

    @api.one
    def action_scrap(self, product_qty, location_id, restrict_lot_id=False, restrict_partner_id=False):
        """ Move the scrap/damaged product into scrap location
        @param product_qty: Scraped product quantity
        @param location_id: Scrap location
        @return: Scraped lines
        """
        res = []
        for move in self:
            new_moves = super(StockMove, self).action_scrap(product_qty, location_id, restrict_lot_id=restrict_lot_id, restrict_partner_id=restrict_partner_id)
            #If we are not scrapping our whole move, tracking and lot references must not be removed
            production_ids = self.env['mrp.production'].search([('move_lines', 'in', [move.id])])
            for prod_id in production_ids:
                prod_id.signal_workflow('button_produce')
            for new_move in new_moves:
                production_ids.write({'move_lines': [(4, new_move)]})
                res.append(new_move)
        return res

    @api.multi
    def write(self, vals):
        res = super(StockMove, self).write(vals)
        from openerp import workflow
        if vals.get('state') == 'assigned':
            orders = list(set([x.raw_material_production_id.id for x in self if x.raw_material_production_id and x.raw_material_production_id.state == 'confirmed']))
            for order_id in orders:
                if self.env['mrp.production'].browse(order_id).test_ready():
                    workflow.trg_validate(self.env.uid, 'mrp.production', order_id, 'moves_ready', self.env.cr)
        return res
