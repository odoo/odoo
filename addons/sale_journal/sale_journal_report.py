# -*- coding: utf-8 -*-
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

from osv import fields,osv

class report_sale_journal_sale(osv.osv):
    _name = "sale_journal.sale.stats"
    _description = "Sales Orders by Journal"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'state': fields.selection([
            ('draft','Quotation'),
            ('waiting_date','Waiting Schedule'),
            ('manual','Manual in progress'),
            ('progress','In progress'),
            ('shipping_except','Shipping Exception'),
            ('invoice_except','Invoice Exception'),
            ('done','Done'),
            ('cancel','Cancel')
        ], 'Order State', readonly=True),
        'journal_id':fields.many2one('sale_journal.sale.journal', 'Journal', readonly=True),
        'quantity': fields.float('Quantities', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'price_average': fields.float('Average Price', readonly=True),
        'count': fields.integer('# of Lines', readonly=True),
    }
    _order = 'journal_id,name desc,price_total desc'
    def init(self, cr):
        cr.execute("""
            create or replace view sale_journal_sale_stats as (
                select
                    min(l.id) as id,
                    to_char(s.date_order, 'YYYY-MM-01') as name,
                    s.state,
                    s.journal_id,
                    sum(l.product_uom_qty) as quantity,
                    count(*),
                    sum(l.product_uom_qty*l.price_unit) as price_total,
                    (sum(l.product_uom_qty*l.price_unit)/sum(l.product_uom_qty))::decimal(16,2) as price_average
                from sale_order s
                    right join sale_order_line l on (s.id=l.order_id)
                group by s.journal_id, to_char(s.date_order, 'YYYY-MM-01'),s.state
            )
        """)
report_sale_journal_sale()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

