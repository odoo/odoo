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

class auction_lots_cancel(osv.osv):
        '''
        OpenERP Model
        '''
        _name = 'auction.lots.cancel'
        _description = 'To cancel auction lots.'

        def cancel(self, cr, uid, ids, context=None):
            """
            To cancel the auction lot

            @param self: The object pointer.
            @param cr: A database cursor
            @param uid: ID of the user currently logged in
            @param ids: List of IDs selected
            @param context: A standard dictionary
            @return:
            """
            if context is None:
                context={}
            lots_obj = self.pool.get('auction.lots')
            invoice_obj = self.pool.get('account.invoice')
            lot = lots_obj.browse(cr, uid, context.get('active_id', False), context=context)
            if lot.ach_inv_id:
                    supplier_refund_inv_id = invoice_obj.refund(cr, uid, [lot.ach_inv_id.id])
            if lot.sel_inv_id:
                    customer_refund_inv_id = invoice_obj.refund(cr, uid, [lot.sel_inv_id.id])
            return {}
                
        _columns = {
        }
auction_lots_cancel()