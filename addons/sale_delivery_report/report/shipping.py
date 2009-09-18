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

import time
from report import report_sxw
from osv import osv
import pooler

class shipping(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(shipping, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
#            'get_address': self._get_address,
#            'get_address_ship':self._get_address_ship
        })

#    def _get_address(self,data):
#
#         self.cr.execute("select sp.id,sp.origin,sp.address_id,so.partner_id,rp.name as name2,so.partner_invoice_id,rpa.name,rpa.street as Street,rpa.city ,rpa.zip,rc.name as country " \
#                         "from sale_order as so, stock_picking as sp,res_partner rp,res_partner_address as rpa,res_country as rc " \
#                         "where sp.origin=so.name " \
#                         "and so.partner_id=rp.id " \
#                         "and so.partner_invoice_id=rpa.id  " \
#                         "and rpa.country_id=rc.id " \
#                         "and sp.id=%s", (data.id,))
#
#         add=self.cr.dictfetchall()
#         return add
#
#    def _get_address_ship(self,data):
#
#         self.cr.execute("select sp.id,sp.origin,sp.address_id,so.partner_id,rp.name as name2,so.partner_shipping_id,rpa.name,rpa.street as Street,rpa.city ,rpa.zip,rc.name as country " \
#                         "from sale_order as so, stock_picking as sp,res_partner rp,res_partner_address as rpa,res_country as rc " \
#                         "where sp.origin=so.name " \
#                         "and so.partner_id=rp.id " \
#                         "and so.partner_shipping_id=rpa.id  " \
#                         "and rpa.country_id=rc.id " \
#                         "and sp.id=%s", (data.id,))
#
#         ship=self.cr.dictfetchall()
#         return ship

#    def _sum_total(self,data):
#        print "======data=======",data

#        self.cr.execute("SELECT sum(pt.list_price*sm.product_qty) FROM stock_picking as sp "\
#                        "LEFT JOIN  stock_move sm ON (sp.id = sm.picking_id) "\
#                        "LEFT JOIN  product_product pp ON (sm.product_id = pp.id) "\
#                        "LEFT JOIN  product_template pt ON (pp.product_tmpl_id = pt.id) "\
#                        "WHERE sm.picking_id = %s", (data['id'],))
#        sum_total = self.cr.fetchone()[0] or 0.00
#        return True

report_sxw.report_sxw('report.sale.shipping','stock.picking','addons/sale_delivery_report/report/shipping.rml',parser=shipping)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
