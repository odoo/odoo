# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from mx import DateTime
from osv import fields
from osv import osv
from tools.translate import _
import ir
import netsvc
import time


class stock_warehouse_orderpoint(osv.osv):
    """
    Defines Minimum stock rules.
    """
    _name = "stock.warehouse.orderpoint"
    _description = "Orderpoint minimum rule"
    
    _columns = {
        'name': fields.char('Name', size=32, required=True),
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the orderpoint without removing it."),
        'logic': fields.selection([('max','Order to Max'),('price','Best price (not yet active!)')], 'Reordering Mode', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True, ondelete='cascade', domain=[('type','=','product')]),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True ),
        'product_min_qty': fields.float('Min Quantity', required=True,
            help="When the virtual stock goes belong the Min Quantity, Open ERP generates "\
            "a procurement to bring the virtual stock to the Max Quantity."),
        'product_max_qty': fields.float('Max Quantity', required=True,
            help="When the virtual stock goes belong the Min Quantity, Open ERP generates "\
            "a procurement to bring the virtual stock to the Max Quantity."),
        'qty_multiple': fields.integer('Qty Multiple', required=True,
            help="The procurement quantity will by rounded up to this multiple."),
        'procurement_id': fields.many2one('mrp.procurement', 'Latest procurement'),
        'company_id': fields.many2one('res.company','Company',required=True),
    }
    _defaults = {
        'active': lambda *a: 1,
        'logic': lambda *a: 'max',
        'qty_multiple': lambda *a: 1,
        'name': lambda x,y,z,c: x.pool.get('ir.sequence').get(y,z,'mrp.warehouse.orderpoint') or '',
        'product_uom': lambda sel, cr, uid, context: context.get('product_uom', False),
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.warehouse.orderpoint', context=c)
    }
    
    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, context={}):
        """ Finds location id for changed warehouse.
        @param warehouse_id: Changed id of warehouse.
        @return: Dictionary of values.
        """
        if warehouse_id:
            w = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context)
            v = {'location_id': w.lot_stock_id.id}
            return {'value': v}
        return {}
    
    def onchange_product_id(self, cr, uid, ids, product_id, context={}):
        """ Finds UoM for changed product.
        @param product_id: Changed id of product.
        @return: Dictionary of values.
        """
        if product_id:
            prod = self.pool.get('product.product').browse(cr,uid,product_id)
            v = {'product_uom': prod.uom_id.id}
            return {'value': v}
        return {}
    
    def copy(self, cr, uid, id, default=None,context={}):
        if not default:
            default = {}
        default.update({
            'name': self.pool.get('ir.sequence').get(cr, uid, 'mrp.warehouse.orderpoint') or '',
        })
        return super(stock_warehouse_orderpoint, self).copy(cr, uid, id, default, context)
    
stock_warehouse_orderpoint()

class StockMove(osv.osv):
    _inherit = 'stock.move'
    
    _columns = {
        'production_id': fields.many2one('mrp.production', 'Production', select=True),
        'procurements': fields.one2many('mrp.procurement', 'move_id', 'Procurements'),
    }
    
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default['procurements'] = []
        return super(StockMove, self).copy(cr, uid, id, default, context)

    def _action_explode(self, cr, uid, move, context={}):
        """ Explodes pickings.
        @param move: Stock moves
        @return: True
        """
        bom_obj = self.pool.get('mrp.bom')
        move_obj = self.pool.get('stock.move')
        procurement_obj = self.pool.get('mrp.procurement')
        product_obj = self.pool.get('product.product')
        wf_service = netsvc.LocalService("workflow")
        if move.product_id.supply_method == 'produce' and move.product_id.procure_method == 'make_to_order':
            bis = bom_obj.search(cr, uid, [
                ('product_id','=',move.product_id.id),
                ('bom_id','=',False),
                ('type','=','phantom')])
            if bis:
                factor = move.product_qty
                bom_point = bom_obj.browse(cr, uid, bis[0])
                res = bom_obj._bom_explode(cr, uid, bom_point, factor, [])
                dest = move.product_id.product_tmpl_id.property_stock_production.id
                state = 'confirmed'
                if move.state == 'assigned':
                    state = 'assigned'
                for line in res[0]:                    
                    valdef = {
                        'picking_id': move.picking_id.id,
                        'product_id': line['product_id'],
                        'product_uom': line['product_uom'],
                        'product_qty': line['product_qty'],
                        'product_uos': line['product_uos'],
                        'product_uos_qty': line['product_uos_qty'],
                        'move_dest_id': move.id,
                        'state': state,
                        'name': line['name'],
                        'location_dest_id': dest,
                        'move_history_ids': [(6,0,[move.id])],
                        'move_history_ids2': [(6,0,[])],
                        'procurements': [],
                    }
                    mid = move_obj.copy(cr, uid, move.id, default=valdef)
                    prodobj = product_obj.browse(cr, uid, line['product_id'], context=context)
                    proc_id = procurement_obj.create(cr, uid, {
                        'name': (move.picking_id.origin or ''),
                        'origin': (move.picking_id.origin or ''),
                        'date_planned': move.date_planned,
                        'product_id': line['product_id'],
                        'product_qty': line['product_qty'],
                        'product_uom': line['product_uom'],
                        'product_uos_qty': line['product_uos'] and line['product_uos_qty'] or False,
                        'product_uos':  line['product_uos'],
                        'location_id': move.location_id.id,
                        'procure_method': prodobj.procure_method,
                        'move_id': mid,
                        'company_id': line['company_id'],
                    })
                    wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
                move_obj.write(cr, uid, [move.id], {
                    'location_id': move.location_dest_id.id,
                    'auto_validate': True,
                    'picking_id': False,
                    'location_id': dest,
                    'state': 'waiting'
                })
                for m in procurement_obj.search(cr, uid, [('move_id','=',move.id)], context):
                    wf_service.trg_validate(uid, 'mrp.procurement', m, 'button_wait_done', cr)
        return True
    
    def action_consume(self, cr, uid, ids, product_qty, location_id=False, context=None): 
        """ Consumed product with specific quatity from specific source location.
        @param product_qty: Consumed product quantity
        @param location_id: Source location
        @return: Consumed lines
        """       
        res = []
        production_obj = self.pool.get('mrp.production')
        wf_service = netsvc.LocalService("workflow")
        for move in self.browse(cr, uid, ids):
            new_moves = super(StockMove, self).action_consume(cr, uid, [move.id], product_qty, location_id, context=context)
            production_ids = production_obj.search(cr, uid, [('move_lines', 'in', [move.id])])
            for prod in production_obj.browse(cr, uid, production_ids, context=context):
                if prod.state == 'confirmed':
                    production_obj.force_production(cr, uid, [prod.id])
                wf_service.trg_validate(uid, 'mrp.production', prod.id, 'button_produce', cr)
            for new_move in new_moves:
                production_obj.write(cr, uid, production_ids, {'move_lines': [(4, new_move)]})
                res.append(new_move)
        return res
    
    def action_scrap(self, cr, uid, ids, product_qty, location_id, context=None):
        """ Move the scrap/damaged product into scrap location
        @param product_qty: Scraped product quantity
        @param location_id: Scrap location
        @return: Scraped lines
        """  
        res = []
        production_obj = self.pool.get('mrp.production')
        wf_service = netsvc.LocalService("workflow")
        for move in self.browse(cr, uid, ids):
            new_moves = super(StockMove, self).action_scrap(cr, uid, [move.id], product_qty, location_id, context=context)
            production_ids = production_obj.search(cr, uid, [('move_lines', 'in', [move.id])])
            for prod_id in production_ids:
                wf_service.trg_validate(uid, 'mrp.production', prod_id, 'button_produce', cr)
            for new_move in new_moves:
                production_obj.write(cr, uid, production_ids, {'move_lines': [(4, new_move)]})
                res.append(new_move)
        return {}

StockMove()


class StockPicking(osv.osv):
    _inherit = 'stock.picking'

    def test_finnished(self, cursor, user, ids):
        wf_service = netsvc.LocalService("workflow")
        res = super(StockPicking, self).test_finnished(cursor, user, ids)
        for picking in self.browse(cursor, user, ids):
            for move in picking.move_lines:
                if move.state == 'done' and move.procurements:
                    for procurement in move.procurements:
                        wf_service.trg_validate(user, 'mrp.procurement',
                                procurement.id, 'button_check', cursor)
        return res

    #
    # Explode picking by replacing phantom BoMs
    #
    def action_explode(self, cr, uid, picks, *args):
        """ Explodes picking by replacing phantom BoMs
        @param picks: Picking ids. 
        @param *args: Arguments
        @return: Picking ids.
        """  
        move_obj = self.pool.get('stock.move')
        for move in move_obj.browse(cr, uid, picks):
            move_obj._action_explode(cr, uid, move)
        return picks

StockPicking()


class spilt_in_production_lot(osv.osv_memory):
    _inherit = "stock.move.split"
    
    def split(self, cr, uid, ids, move_ids, context=None):
        """ Splits move lines into given quantities.
        @param move_ids: Stock moves.
        @return: List of new moves.
        """  
        production_obj = self.pool.get('mrp.production')
        move_obj = self.pool.get('stock.move')  
        res = []      
        for move in move_obj.browse(cr, uid, move_ids, context=context):
            new_moves = super(spilt_in_production_lot, self).split(cr, uid, ids, move_ids, context=context)
            production_ids = production_obj.search(cr, uid, [('move_lines', 'in', [move.id])])
            for new_move in new_moves:
                production_obj.write(cr, uid, production_ids, {'move_lines': [(4, new_move)]})                
        return res
    
spilt_in_production_lot()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
