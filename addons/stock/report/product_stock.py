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

from datetime import datetime
from dateutil.relativedelta import relativedelta

import openerp
from openerp import osv
import time
from openerp.report.interface import report_int
from openerp.report.render import render

import stock_graph
import StringIO
import unicodedata

class external_pdf(render):
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'

    def _render(self):
        return self.pdf


class report_stock(report_int):
    def create(self, cr, uid, ids, datas, context=None):
        if context is None:
            context = {}
        registry = openerp.registry(cr.dbname)
        product_ids = ids
        if 'location_id' in context:
            location_id = context['location_id']
        else:
            warehouse_id = registry['stock.warehouse'].search(cr, uid, [])[0]
            location_id = registry['stock.warehouse'].browse(cr, uid, warehouse_id).lot_stock_id.id

        loc_ids = registry['stock.location'].search(cr, uid, [('location_id','child_of',[location_id])])

        now = time.strftime('%Y-%m-%d')
        dt_from = now
        dt_to = now

        names = dict(registry['product.product'].name_get(cr, uid, product_ids))
        for name in names:
            names[name] = names[name].encode('utf8')
        products = {}
        ctx = context.copy()
        ctx['location_id'] = loc_ids
        prods = registry['product.product']._product_available(cr, uid, product_ids, context=ctx)
        for prod in prods.keys():
            products[prod] = [(now, prods[prod]['qty_available'])]
            prods[prod] = 0


        if not loc_ids or not product_ids:
            return (False, 'pdf')

        cr.execute("select sum(r.product_qty * u.factor), r.date, r.product_id "
                   "from stock_move r left join product_uom u on (r.product_uom=u.id) "
                   "where state IN %s"
                   "and location_id IN %s"
                   "and product_id IN %s"
                   "group by date,product_id",(('confirmed','assigned','waiting'),tuple(loc_ids) ,tuple(product_ids),))
        for (qty, dt, prod_id) in cr.fetchall():
            if dt<=dt_from:
                dt= (datetime.now() + relativedelta(days=1)).strftime('%Y-%m-%d')
            else:
                dt = dt[:10]
            products.setdefault(prod_id, [])
            products[prod_id].append((dt,-qty))

        cr.execute("select sum(r.product_qty * u.factor), r.date, r.product_id "
                   "from stock_move r left join product_uom u on (r.product_uom=u.id) "
                   "where state IN %s"
                   "and location_dest_id IN %s"
                   "and product_id IN %s"
                   "group by date,product_id",(('confirmed','assigned','waiting'),tuple(loc_ids) ,tuple(product_ids),))

        for (qty, dt, prod_id) in cr.fetchall():
            if dt<=dt_from:
                dt= (datetime.now() + relativedelta(days=1)).strftime('%Y-%m-%d')
            else:
                dt = dt[:10]
            products.setdefault(prod_id, [])
            products[prod_id].append((dt,qty))

        dt = dt_from
        qty = 0

        io = StringIO.StringIO()
        gt = stock_graph.stock_graph(io)
        for prod_id in products:
            prod_name = names.get(prod_id,'Unknown')
            if isinstance(prod_name, str):
                 prod_name = prod_name.decode('utf-8')
                 prod_name = unicodedata.normalize('NFKD',prod_name)
                 prod_name = prod_name.encode('ascii','replace')
            gt.add(prod_id, prod_name, products[prod_id])   
        gt.draw()
        gt.close()
        self.obj = external_pdf(io.getvalue())
        self.obj.render()
        return (self.obj.pdf, 'pdf')
report_stock('report.stock.product.history')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

