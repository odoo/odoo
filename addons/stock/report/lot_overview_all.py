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

class lot_overview_all(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(lot_overview_all, self).__init__(cr, uid, name, context)
        self.price_total = 0.0
        self.localcontext.update({
            'time': time,
            'process':self.process,
            'price_total': self._price_total,
        })

    def process(self,location_id):
        res = {}
        location_obj = pooler.get_pool(self.cr.dbname).get('stock.location')
        product_obj = pooler.get_pool(self.cr.dbname).get('product.product')
       
        product_ids = product_obj.search(self.cr, self.uid, [])

        products = product_obj.browse(self.cr,self.uid, product_ids)
        products_by_uom = {}
        products_by_id = {}
        for product in products:
            products_by_uom.setdefault(product.uom_id.id, [])
            products_by_uom[product.uom_id.id].append(product)
            products_by_id.setdefault(product.id, [])
            products_by_id[product.id] = product

        result = []
#        res['prod'] = []
        for id in self.ids:
            for uom_id in products_by_uom.keys():
                fnc = location_obj._product_get
                qty = fnc(self.cr, self.uid, id, [x.id for x in products_by_uom[uom_id]])
                for product_id in qty.keys():
                    if not qty[product_id]:
                        continue
                    product = products_by_id[product_id]
                    value=(product.standard_price)*(qty[product_id])
                    self.price_total += value
                    result.append({
                        
                        'name': product.name,
                        'variants': product.variants or '',
                        'code': product.default_code,
                       'amount': str(qty[product_id]),
                        'uom': product.uom_id.name,
                        'price': str(product.standard_price),
                        'value':str(value),
                    })
                    
        
        return result
    
    def _price_total(self):
            return str( self.price_total)

report_sxw.report_sxw('report.lot.stock.overview_all', 'stock.location', 'addons/stock/report/lot_overview_all.rml', parser=lot_overview_all)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

