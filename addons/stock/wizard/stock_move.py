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

from osv import fields, osv
from tools.translate import _

class stock_move_track(osv.osv_memory):
    _name = "stock.move.track"
    _description = "Track moves"
    
    _columns = {
        'tracking_prefix': fields.char('Tracking prefix', size=64), 
        'quantity': fields.float("Quantity per lot")
              }

    _defaults = {
        'quantity': lambda *x: 1
                 }
    
    def track_lines(self, cr, uid, ids, context={}):
        """ 
             To track stock moves lines
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs if we want more than one 
             @param context: A standard dictionary 
             
             @return: 
        
        """                
        datas = self.read(cr, uid, ids)[0]
        move_obj = self.pool.get('stock.move')
        move_obj._track_lines(cr, uid, context['active_id'], datas, context=context)
        return {}

stock_move_track()

class stock_move_consume(osv.osv_memory):
    _name = "stock.move.consume"
    _description = "Consume Products"
    
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True), 
        'product_qty': fields.float('Quantity', required=True), 
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True), 
        'location_id': fields.many2one('stock.location', 'Location', required=True)
    }

    def default_get(self, cr, uid, fields, context=None):
        """ 
             Get default values
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param fields: List of fields for default value 
             @param context: A standard dictionary 
             
             @return: default values of fields
        
        """
        res = super(stock_move_consume, self).default_get(cr, uid, fields, context=context)        
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})     
        if 'product_uom' in fields:
            res.update({'product_uom': move.product_uom.id})    
        if 'product_qty' in fields:
            res.update({'product_qty': move.product_qty.id})    
        if 'location_id' in fields:
            res.update({'location_id': move.location_id.id})
        return res   
            
    def do_move_consume(self, cr, uid, ids, context={}):
        """ 
             To move consumed products
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs if we want more than one 
             @param context: A standard dictionary 
             
             @return: 
        
        """              
        move_obj = self.pool.get('stock.move')
        move_ids = context['active_ids']
        for data in self.read(cr, uid, ids):            
            move_obj.action_consume(cr, uid, move_ids, 
                             data['product_qty'], data['location_id'], 
                             context=context)
        return {}

stock_move_consume()


class stock_move_scrap(osv.osv_memory):
    _name = "stock.move.scrap"
    _description = "Scrap Products"
    _inherit = "stock.move.consume"
    
    _defaults = {
                 'location_id': lambda *x: False
    }

    def move_scrap(self, cr, uid, ids, context={}):
        """ 
             To move scraped products
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs if we want more than one 
             @param context: A standard dictionary 
             
             @return: 
        
        """              
        move_obj = self.pool.get('stock.move')        
        move_ids = context['active_ids']
        for data in self.read(cr, uid, ids):
            move_obj.action_scrap(cr, uid, move_ids, 
                             data['product_qty'], data['location_id'], 
                             context=context)
        return {}

stock_move_scrap()


class split_in_production_lot(osv.osv_memory):
    _name = "stock.move.split"
    _description = "Split in Production lots"
    
    def default_get(self, cr, uid, fields, context=None):
        """ 
             Get default values
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param fields: List of fields for default value 
             @param context: A standard dictionary 
             
             @return: default values of fields
        
        """
        
        res = super(split_in_production_lot, self).default_get(cr, uid, fields, context=context)        
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)  
        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})  
        return res
    
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'line_ids': fields.one2many('stock.move.split.lines', 'lot_id', 'Lots Number')
     }
    def split_lot(self, cr, uid, ids, context=None):
        """ 
             To split a lot
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs if we want more than one 
             @param context: A standard dictionary 
             
             @return: 
        
        """                    
        self.split(cr, uid, ids, context.get('active_ids'), context=context)
        return {}

    def split(self, cr, uid, ids, move_ids, context=None):
        """ 
             To split stock moves into production lot
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs if we want more than one 
             @param move_ids: the ID or list of IDs of stock move we want to split
             @param context: A standard dictionary 
             
             @return: 
        
        """                    
        prodlot_obj = self.pool.get('stock.production.lot')
        ir_sequence_obj = self.pool.get('ir.sequence')
        move_obj = self.pool.get('stock.move')
        new_move = []        
        for data in self.browse(cr, uid, ids):
            for move in move_obj.browse(cr, uid, move_ids):
                move_qty = move.product_qty
                quantity_rest = move.product_qty
                uos_qty_rest = move.product_uos_qty
                new_move = []                            
                for line in data.line_ids:
                    quantity = line.quantity
                    

                    if quantity <= 0 or move_qty == 0:
                        continue
                    quantity_rest -= quantity
                    uos_qty = quantity / move_qty * move.product_uos_qty
                    uos_qty_rest = quantity_rest / move_qty * move.product_uos_qty
                    if quantity_rest <= 0:
                        quantity_rest = quantity
                        break
                    default_val = {
                        'product_qty': quantity, 
                        'product_uos_qty': uos_qty, 
                        'state': move.state
                    }
                    current_move = move_obj.copy(cr, uid, move.id, default_val)
                    new_move.append(current_move)
                    prodlot_id = False
                    if line.use_exist and line.name:
                        prodlot_id = prodlot_obj.search(cr, uid, [('prefix','=',line.name),('product_id','=',data.product_id.id)])
                        if prodlot_id:
                            prodlot_id = prodlot_id[0]                    
                    if not prodlot_id:
                        sequence = ir_sequence_obj.get(cr, uid, 'stock.lot.serial')
                        prodlot_id = prodlot_obj.create(cr, uid, {'name': sequence, 'prefix' : line.name}, 
                                                 {'product_id': move.product_id.id})                    
                    move_obj.write(cr, uid, [current_move], {'prodlot_id': prodlot_id})
                    prodlot = prodlot_obj.browse(cr, uid, prodlot_id) 
                    ref = '%d' % (move.id)
                    if prodlot.ref:
                        ref = '%s, %s' % (prodlot.ref, ref) 
                    prodlot_obj.write(cr, uid, [prodlot_id], {'ref': ref})
                    
                    update_val = {}
                    if quantity_rest > 0:                        
                        update_val['product_qty'] = quantity_rest
                        update_val['product_uos_qty'] = uos_qty_rest                          
                        move_obj.write(cr, uid, [move.id], update_val)
        return new_move
split_in_production_lot()

class stock_move_split_lines(osv.osv_memory):
    _name = "stock.move.split.lines"
    _description = "Split lines"
    
    _columns = {
        'name': fields.char('Tracking serial', size=64), 
        'quantity': fields.integer('Quantity'), 
        'use_exist' : fields.boolean('Use Exist'),
        'lot_id': fields.many2one('stock.move.split', 'Lot'),
        'action': fields.selection([('split','Split'),('keepinone','Keep in one lot')],'Action'),
    }
    _defaults = {
        'quantity': lambda *x: 1,
        'action' : lambda *x: 'split', 
    }

stock_move_split_lines()
