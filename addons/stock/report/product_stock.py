# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from mx import DateTime

import osv
import time
from report.interface import report_int
from report.render import render

import stock_graph
import pooler
import StringIO

class external_pdf(render):
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'
    
    def _render(self):
        return self.pdf


class report_stock(report_int):
    def create(self, cr, uid, ids, datas, context={}):
        product_ids = ids
        if 'location_id' in context:
            location_id = context['location_id']
        else:
            warehouse_id = pooler.get_pool(cr.dbname).get('stock.warehouse').search(cr, uid, [])[0]
            location_id = pooler.get_pool(cr.dbname).get('stock.warehouse').browse(cr, uid, warehouse_id).lot_stock_id.id

        loc_ids = pooler.get_pool(cr.dbname).get('stock.location').search(cr, uid, [('location_id','child_of',[location_id])])

        loc_ids_s = ','.join(map(str,loc_ids))
        now = time.strftime('%Y-%m-%d')
        dt_from = now
        dt_to = now

        names = dict(pooler.get_pool(cr.dbname).get('product.product').name_get(cr, uid, product_ids))
        products = {}
        prods = pooler.get_pool(cr.dbname).get('stock.location')._product_all_get(cr, uid, location_id, product_ids)
        prod_ids_s = ','.join(map(str,product_ids))

        for p in prods:
            products[p] = [(now,prods[p])]
            prods[p] = 0

        cr.execute("select sum(r.product_qty * u.factor), r.date_planned, r.product_id from stock_move r left join product_uom u on (r.product_uom=u.id) where state in ('confirmed','assigned','waiting') and location_id in ("+loc_ids_s+") and product_id in ("+prod_ids_s+") group by date_planned,product_id")

        for (qty, dt, prod_id) in cr.fetchall():
            if dt<=dt_from:
                dt= (DateTime.now() + DateTime.RelativeDateTime(days=1)).strftime('%Y-%m-%d')
            else:
                dt = dt[:10]
            products.setdefault(prod_id, [])
            products[prod_id].append((dt,-qty))

        cr.execute("select sum(r.product_qty * u.factor), r.date_planned, r.product_id from stock_move r left join product_uom u on (r.product_uom=u.id) where state in ('confirmed','assigned','waiting') and location_dest_id in ("+loc_ids_s+") and product_id in ("+prod_ids_s+") group by date_planned,product_id")
        for (qty, dt, prod_id) in cr.fetchall():
            if dt<=dt_from:
                dt= (DateTime.now() + DateTime.RelativeDateTime(days=1)).strftime('%Y-%m-%d')
            else:
                dt = dt[:10]
            products.setdefault(prod_id, [])
            products[prod_id].append((dt,qty))

        dt = dt_from
        qty = 0

        io = StringIO.StringIO()
        gt = stock_graph.stock_graph(io)
        for prod_id in products:
            gt.add(prod_id, names.get(prod_id, 'Unknown'), products[prod_id])
        gt.draw()
        gt.close()
        self.obj = external_pdf(io.getvalue())
        self.obj.render()
        return (self.obj.pdf, 'pdf')
report_stock('report.stock.product.history')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

