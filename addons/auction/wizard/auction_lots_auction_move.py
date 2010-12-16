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
import netsvc
import pooler
import time
import tools
import wizard

class auction_lots_auction_move(osv.osv_memory):
    """Auction Move"""
    _name = "auction.lots.auction.move"
    _description = __doc__
    _columns= {
        'auction_id':fields.many2one('auction.dates', 'Auction Date', required=True),
    }

    def auction_move_set(self, cr, uid, ids, context=None):
        """
        This Function update auction date on auction lots to given auction date.
        erase the auction lots's object adjudication price and its buyer and change state to draft.
        create new entry in auction lot history.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of auction lots auction move’s IDs.
        """
        if context is None:
            context={}
        auction_bid_line_obj = self.pool.get('auction.bid_line')
        auction_lot_history_obj = self.pool.get('auction.lot.history')
        auction_lots_obj = self.pool.get('auction.lots')
        rec_ids =  auction_lots_obj.browse(cr, uid, context.get('active_ids', []))
        for current in self.browse(cr, uid, ids, context=context):
            if not (current.auction_id and len(context.get('active_ids', []))):
                return {}

            for rec in rec_ids:
                new_id = auction_lot_history_obj.create(cr, uid, {
                    'auction_id': rec.auction_id.id,
                    'lot_id': rec.id,
                    'price': rec.obj_ret
                    })
                up_auction = auction_lots_obj.write(cr, uid, [rec.id], {
                    'auction_id': current.auction_id.id,
                    'obj_ret': None,
                    'obj_price': None,
                    'ach_login': None,
                    'ach_uid': None,
                    'ach_inv_id': None,
                    'sel_inv_id': None,
                    'obj_num': None,
                    'state': 'draft'})
            return {}

auction_lots_auction_move()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

