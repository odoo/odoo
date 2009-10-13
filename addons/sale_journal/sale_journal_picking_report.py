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

class report_sale_journal_invoice_type_stats(osv.osv):
    _name = "sale_journal.invoice.type.stats"
    _description = "Stats on packing by invoice method"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'invoice_state':fields.selection([
            ("invoiced","invoiced"),
            ("2binvoiced","to be invoiced"),
            ("none","None")
        ], "Invoice state", readonly=True),
        'state': fields.selection([
            ('draft','draft'),
            ('auto','waiting'),
            ('confirmed','confirmed'),
            ('assigned','assigned'),
            ('done','done'),
            ('cancel','cancel'),
        ], 'State', readonly=True),
        'invoice_type_id':fields.many2one('sale_journal.invoice.type', 'Invoicing method', readonly=True),
        'quantity': fields.float('Quantities', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'price_average': fields.float('Average Price', readonly=True),
        'count': fields.integer('# of Lines', readonly=True),
    }
    _order = 'state,invoice_state,name desc'
    def init(self, cr):
        cr.execute("""
            create or replace view sale_journal_invoice_type_stats as (
                select
                    min(l.id) as id,
                    to_char(s.date, 'YYYY-MM-01') as name,
                    s.state,
                    s.invoice_state,
                    s.invoice_type_id,
                    sum(l.product_qty) as quantity,
                    count(*) as count,
                    sum(l.product_qty*ol.price_unit*(1.0-ol.discount/100.0)) as price_total,
                    (sum(l.product_qty*ol.price_unit*(1.0-ol.discount/100.0))/sum(l.product_qty))::decimal(16,2) as price_average
                from stock_picking s
                    left join stock_move l on (s.id=l.picking_id)
                    left join sale_order_line ol on (l.sale_line_id=ol.id)
                group by s.invoice_type_id, to_char(s.date, 'YYYY-MM-01'),s.state, s.invoice_state
                order by s.invoice_type_id, s.invoice_state, s.state
            )
        """)
report_sale_journal_invoice_type_stats()

class report_sale_journal_picking(osv.osv):
    _name = "sale_journal.picking.stats"
    _description = "Packing lists by Journal"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'state': fields.selection([
            ('draft','draft'),
            ('auto','waiting'),
            ('confirmed','confirmed'),
            ('assigned','assigned'),
            ('done','done'),
            ('cancel','cancel'),
        ], 'State', readonly=True),
        'journal_id':fields.many2one('sale_journal.picking.journal', 'Journal', readonly=True),
        'quantity': fields.float('Quantities', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'price_average': fields.float('Average Price', readonly=True),
        'count': fields.integer('# of Lines', readonly=True),
    }
    _order = 'journal_id,name desc,price_total desc'
    def init(self, cr):
        cr.execute("""
            create or replace view sale_journal_picking_stats as (
                select
                    min(l.id) as id,
                    to_char(s.date, 'YYYY-MM-01') as name,
                    s.state,
                    s.journal_id,
                    sum(l.product_qty) as quantity,
                    count(*) as count,
                    sum(l.product_qty*ol.price_unit*(1.0-ol.discount/100.0)) as price_total,
                    (sum(l.product_qty*ol.price_unit*(1.0-ol.discount/100.0))/sum(l.product_qty))::decimal(16,2) as price_average
                from stock_picking s
                    right join stock_move l on (s.id=l.picking_id)
                    right join sale_order_line ol on (l.sale_line_id=ol.id)
                group by s.journal_id, to_char(s.date, 'YYYY-MM-01'),s.state
            )
        """)
report_sale_journal_picking()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

