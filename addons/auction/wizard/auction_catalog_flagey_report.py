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

from osv import osv, fields
import netsvc
from tools.translate import _

class auction_catalog_flagey(osv.osv_memory):
    _name = 'auction.catalog.flagey'
    _description = 'Auction Catalog Flagey'
    
    def default_get(self, cr, uid, fields, context=None):
        """ 
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values 
         @param context: A standard dictionary 
         @return: A dictionary which of fields with values. 
        """
        res = super(auction_catalog_flagey, self).default_get(cr, uid, fields, context=context)
        return res
    
    def view_init(self, cr, uid, fields, context=None):
        """ 
         Creates view dynamically, adding fields at runtime, raises exception
         at the time of initialization of view.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary 
         @return: New arch of view with new columns.
        """
        lots_obj = self.pool.get('auction.lots')
        auc_dates_obj = self.pool.get('auction.dates')
        if context is None: context = {}
        current_auction = auc_dates_obj.browse(cr, uid, context.get('active_ids', []))
        v_lots = lots_obj.search(cr, uid, [('auction_id','=',current_auction.id)])
        v_ids = lots_obj.browse(cr, uid, v_lots, context=context)
        for ab in v_ids:
            if not ab.auction_id :
                raise osv.except_osv(_('Error!'), _('No Lots belong to this Auction Date'))
        pass
    
    def print_report(self, cr, uid, ids, context=None):
        """ 
         Prints auction catalog flagey report.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of IDs selected 
         @param context: A standard dictionary 
         @return: Report  
        """
        if context is None: context = {}
        datas = {'ids': context.get('active_ids',[])}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'auction.cat_flagy',
            'datas': datas,
        }
    
auction_catalog_flagey()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

