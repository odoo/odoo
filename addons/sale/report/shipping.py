# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

import time
from report import report_sxw
from osv import osv
import pooler

class shipping(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(shipping, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
#            'sum_total': self._sum_total,
        })
        
#    def _sum_total(self,data):
#        print "======data=======",data['id']
#        self.cr.execute("SELECT sum(pt.list_price*sm.product_qty) FROM stock_picking as sp "\
#                        "LEFT JOIN  stock_move sm ON (sp.id = sm.picking_id) "\
#                        "LEFT JOIN  product_product pp ON (sm.product_id = pp.id) "\
#                        "LEFT JOIN  product_template pt ON (pp.product_tmpl_id = pt.id) "\
#                        "WHERE sm.picking_id = %d "%(data['id']))
#        sum_total = self.cr.fetchone()[0] or 0.00
#        return sum_total

report_sxw.report_sxw('report.sale.shipping','stock.picking','addons/sale/report/shipping.rml',parser=shipping)
