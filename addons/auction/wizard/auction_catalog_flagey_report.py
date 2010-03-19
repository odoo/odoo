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

class auction_catalog_flagey(osv.osv_memory):
    _name = 'auction.catalog.flagey'
    _description = 'Auction Catalog Flagey'
    
    def default_get(self, cr, uid, fields, context):
        res = super(auction_catalog_flagey, self).default_get(cr, uid, fields, context=context)
        return res
    
    def view_init(self, cr, uid, fields_list, context):
        current_auction = self.pool.get('auction.dates').browse(cr,uid,context.get('active_ids', []))
        v_lots = self.pool.get('auction.lots').search(cr,uid,[('auction_id','=',current_auction.id)])
        v_ids = self.pool.get('auction.lots').browse(cr,uid,v_lots)
        for ab in v_ids:
            if not ab.auction_id :
                raise osv.except_osv('Error!','No Lots belong to this Auction Date')
        pass
    
    def print_report(self, cr, uid, ids, context):
        datas = {'ids': context.get('active_ids',[])}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'auction.cat_flagy',
            'datas': datas,
        }
    
auction_catalog_flagey()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

