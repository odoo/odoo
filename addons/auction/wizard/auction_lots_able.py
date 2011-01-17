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

class auction_lots_able(osv.osv_memory):
    
    _name = "auction.lots.able"
    _description = "Lots able"
    
    def confirm_able(self, cr, uid, ids, context=None):
        """
            This function Update auction lots object and set taken away field true.
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of auction lots able’s IDs.
        """
        if context is None: 
            context = {}
        self.pool.get('auction.lots').write(cr, uid, context.get('active_ids', []), {'ach_emp':True})
        return {'type': 'ir.actions.act_window_close'}
    
auction_lots_able()
