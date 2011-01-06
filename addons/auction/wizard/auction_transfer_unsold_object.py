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

from osv import osv
from osv import fields

class auction_transfer_unsold_object(osv.osv):
        '''
        OpenERP Model
        '''
        _name = 'auction.transfer.unsold.object'
        _description = 'To transfer unsold objects'

        def _start(self, cr, uid, context=None):
            """ 
            To initialize auction_id_from
            @param self: The object pointer.
            @param cr: A database cursor
            @param uid: ID of the user currently logged in
            @param ids: List of IDs selected 
            @param context: A standard dictionary 
            @return: auction_id_from
            """
            lots_obj = self.pool.get('auction.lots')
            rec = lots_obj.browse(cr, uid, context.get('active_id', False), context=context)
            auction_from = rec and rec.auction_id.id or False
            return  auction_from
        
        _columns = {
                'auction_id_from':fields.many2one('auction.dates', 'From Auction Date', required=True),
                'auction_id_to':fields.many2one('auction.dates', 'To Auction Date', required=True),
        }

        _defaults = {
            'auction_id_from': _start,
        }
        
        def transfer_unsold_object(self, cr, uid, ids, context=None):
            """ 
            To Transfer the unsold object
            @param self: The object pointer.
            @param cr: A database cursor
            @param uid: ID of the user currently logged in
            @param ids: List of IDs selected 
            @param context: A standard dictionary 
            @return: 
            """
            if context is None: context = {}
            bid_line_obj = self.pool.get('auction.bid_line')
            lots_obj = self.pool.get('auction.lots')
            lot_history_obj = self.pool.get('auction.lot.history')
            line_ids= bid_line_obj.search(cr, uid, [('lot_id','in',context.get('active_ids', []))])
            bid_line_obj.unlink(cr, uid, line_ids)
            
            res = self.browse(cr, uid, ids, context=context)        
            unsold_ids = lots_obj.search(cr,uid,[('auction_id','=',res[0].auction_id_from.id),('state','=','unsold')])
            for rec in lots_obj.browse(cr, uid, unsold_ids, context=context):
                new_id = lot_history_obj.create(cr, uid, {'auction_id':rec.auction_id.id,'lot_id':rec.id,'price': rec.obj_ret, 'name': rec.auction_id.auction1})
                up_auction = lots_obj.write(cr, uid, [rec.id], {'auction_id': res[0].auction_id_to.id,
                                                                                                'obj_ret':None,
                                                                                                'obj_price':None,
                                                                                                'ach_login':None,
                                                                                                'ach_uid':None,
                                                                                                'ach_inv_id':None,
                                                                                                'sel_inv_id':None,
                                                                                                'state':'draft'})
            return {'type': 'ir.actions.act_window_close'}    
        
auction_transfer_unsold_object()