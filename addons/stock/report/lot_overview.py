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
from openerp import pooler
import time
from openerp.report import report_sxw

class lot_overview(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(lot_overview, self).__init__(cr, uid, name, context=context)
        self.price_total = 0.0
        self.grand_total = 0.0
        self.localcontext.update({
            'time': time,
            'process':self.process,
            'price_total': self._price_total,
            'grand_total_price':self._grand_total,
        })

    def process(self, location_id):
        location_obj = pooler.get_pool(self.cr.dbname).get('stock.location')
        data = location_obj._product_get_report(self.cr,self.uid, [location_id])

        data['location_name'] = location_obj.read(self.cr, self.uid, [location_id],['complete_name'])[0]['complete_name']
        self.price_total = 0.0
        self.price_total += data['total_price']
        self.grand_total += data['total_price']
        return [data]

    def _price_total(self):
        return self.price_total

    def _grand_total(self):
        return self.grand_total

report_sxw.report_sxw('report.lot.stock.overview', 'stock.location', 'addons/stock/report/lot_overview.rml', parser=lot_overview,header='internal')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

