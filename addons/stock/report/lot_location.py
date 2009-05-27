# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import pooler
import time
from report import report_sxw

class lot_location(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(lot_location, self).__init__(cr, uid, name, context)
        self.quantity_total=0.0
        self.grand_total=0.0

        self.localcontext.update({
            'time': time,
            'process':self.process,
            'qty_total':self._qty_total,
        })

    def process(self,location_id):
        res = {}
        location_obj = pooler.get_pool(self.cr.dbname).get('stock.location')
        product_obj = pooler.get_pool(self.cr.dbname).get('product.product')
        self.quantity_total=0.0
        res['location_name'] = pooler.get_pool(self.cr.dbname).get('stock.location').read(self.cr, self.uid, [location_id],['name'])[0]['name']

        prod_info = location_obj._product_get(self.cr, self.uid, location_id)

        res['product'] = []
        for prod in product_obj.browse(self.cr, self.uid, prod_info.keys()):
            if prod_info[prod.id]:
                res['product'].append({'prod_name': prod.name, 'prod_qty': str(prod_info[prod.id])})
                self.quantity_total+=prod_info[prod.id]
                self.grand_total+=prod_info[prod.id]
        if not res['product']:
            res['product'].append({'prod_name': '', 'prod_qty': ''})
        location_child = location_obj.read(self.cr, self.uid, [location_id], ['child_ids'])
        res['total'] = self.quantity_total
        list=[]
        list.append(res)

        for child_id in location_child[0]['child_ids']:
                list.extend(self.process(child_id))
        return list

    def _qty_total(self):
        return str( self.grand_total)

report_sxw.report_sxw('report.lot.location', 'stock.location', 'addons/stock/report/lot_location.rml', parser=lot_location)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

