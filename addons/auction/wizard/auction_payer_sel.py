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

class auction_payer(osv.osv_memory):
    _name = "auction.payer"
    _description = "Auction payer"
    
    def payer(self, cr, uid, ids, context=None):
        if context is None: 
            context = {}
        self.pool.get('auction.lots').write(cr, uid, context.get('active_ids', []), {'is_ok':True, 'state':'paid'})
        return {'type': 'ir.actions.act_window_close'}
    
auction_payer()

class auction_payer_sel(osv.osv_memory):
    """
    For Mark as payment for seller
    """
    _name = "auction.payer.sel"
    _description = "Auction payment for seller"
    
    def payer_sel(self, cr, uid, ids, context=None):
        """
        This function Update auction lots object and seller paid  true.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of auction payer sel’s IDs.
        """
        if context is None: 
            context = {}
        self.pool.get('auction.lots').write(cr, uid, context.get('active_ids', []), {'paid_vnd':True})
        return {'type': 'ir.actions.act_window_close'}
    
auction_payer_sel()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

