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

class auction_lots_enable(osv.osv_memory):
    _name = "auction.lots.enable"
    _description = "Lots Enable"
    
    _columns= {
        'confirm_en':fields.integer('Catalog Number')
    }
    
    def confirm_enable(self, cr, uid, ids, context=None):
        """
        This function Update auction lots object and set taken away field False.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of auction lots enable’s IDs.
        """
        if context is None: 
            context = {}
        self.pool.get('auction.lots').write(cr, uid, context.get('active_id',False), {'ach_emp':False})
        return {}
    
auction_lots_enable()
