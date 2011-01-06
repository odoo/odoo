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

from osv import osv,fields


class pos_scan_product(osv.osv_memory):
    _name = 'pos.scan.product'
    _description = 'Scan product'
    
    _columns = {
        'gencod': fields.char('Barcode', size=13, required=True)
    }
    
    def scan(self, cr, uid, ids, context=None):
        """ 
         To get the gencod and scan product         
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return : retrun gencod
        """
        if context is None:
            context = {}
        data=self.read(cr, uid, ids)[0]
        record_id = context and context.get('active_id', False)
        self. pool.get('pos.order.line')._scan_product(cr, uid, data['gencod'], 1, record_id)
        return {'gencod': False}

pos_scan_product()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

