# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import pooler
import time
from report import report_sxw

class lot_location(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(lot_location, self).__init__(cr, uid, name, context=context)
        self.grand_total = 0.0

        self.localcontext.update({
            'time': time,
            'process':self.process,
            'qty_total':self._qty_total,
        })

    def process(self,location_id):
        location_obj = pooler.get_pool(self.cr.dbname).get('stock.location')
        data = location_obj._product_get_report(self.cr,self.uid, [location_id])
        data['location_name'] = location_obj.read(self.cr, self.uid, [location_id],['name'])[0]['name']
        self.grand_total += data['total']
        return [data]

    def _qty_total(self):
        return str( self.grand_total)

report_sxw.report_sxw('report.lot.location', 'stock.location', 'addons/stock/report/lot_location.rml', parser=lot_location)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

