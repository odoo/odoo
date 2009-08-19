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

from osv import fields,osv

class report_sale_order_product(osv.osv):
    _name = "report.sale.order.product"
    _description = "Sales Orders by Products"
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
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'quantity': fields.float('# of Products', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'price_average': fields.float('Average Price', readonly=True),
        'count': fields.integer('# of Lines', readonly=True),
    }
    _order = 'name desc,price_total desc'
    def init(self, cr):
        cr.execute("""
            create or replace view report_sale_order_product as (
                select
                    min(l.id) as id,
                    to_char(s.date_order, 'YYYY-MM-01') as name,
                    s.state,
                    l.product_id,
                    sum(l.product_uom_qty*u.factor) as quantity,
                    count(*),
                    sum(l.product_uom_qty*l.price_unit) as price_total,
                    (sum(l.product_uom_qty*l.price_unit)/sum(l.product_uom_qty*u.factor))::decimal(16,2) as price_average
                from sale_order s
                    right join sale_order_line l on (s.id=l.order_id)
                    left join product_uom u on (u.id=l.product_uom)
                where l.product_uom_qty != 0
                group by l.product_id, to_char(s.date_order, 'YYYY-MM-01'),s.state
            )
        """)
report_sale_order_product()

class report_sale_order_category(osv.osv):
    _name = "report.sale.order.category"
    _description = "Sales Orders by Categories"
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
        'category_id': fields.many2one('product.category', 'Categories', readonly=True),
        'quantity': fields.float('# of Products', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'price_average': fields.float('Average Price', readonly=True),
        'count': fields.integer('# of Lines', readonly=True),
    }
    _order = 'name desc,price_total desc'
    def init(self, cr):
        cr.execute("""
            create or replace view report_sale_order_category as (
                select
                    min(l.id) as id,
                    to_char(s.date_order, 'YYYY-MM-01') as name,
                    s.state,
                    t.categ_id as category_id,
                    sum(l.product_uom_qty*u.factor) as quantity,
                    count(*),
                    sum(l.product_uom_qty*l.price_unit) as price_total,
                    (sum(l.product_uom_qty*l.price_unit)/sum(l.product_uom_qty*u.factor))::decimal(16,2) as price_average
                from sale_order s
                    right join sale_order_line l on (s.id=l.order_id)
                    left join product_product p on (p.id=l.product_id)
                    left join product_template t on (t.id=p.product_tmpl_id)
                    left join product_uom u on (u.id=l.product_uom)
                where l.product_uom_qty != 0    
                group by t.categ_id, to_char(s.date_order, 'YYYY-MM-01'),s.state
            )
        """)
report_sale_order_category()

class report_turnover_per_month(osv.osv):
    _name = "report.turnover.per.month"
    _description = "Turnover Per Month"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'turnover': fields.float('Total Turnover', readonly=True),
    }
    
    def init(self, cr):
        cr.execute("""
            create or replace view report_turnover_per_month as (
                select min(am.id) as id, sum(credit) as turnover,to_char(am.date, 'YYYY-MM-01') as name from account_move_line am
                    where am.account_id in (select distinct(account_id) from account_invoice_line) 
                    and 
                    am.move_id in(select distinct(aw.move_id) from account_invoice aw,account_invoice_line l where l.invoice_id=aw.id)
                    group by to_char(am.date, 'YYYY-MM-01')
            )
        """)
report_turnover_per_month()

class report_turnover_per_product(osv.osv):
    _name = "report.turnover.per.product"
    _description = "Turnover Per Product"
    _auto = False
    _rec_name = 'product_id'
    
    _columns = {
        'product_id': fields.many2one('product.product','Product', readonly=True),
        'turnover': fields.float('Total Turnover', readonly=True),
    }
    
    def init(self, cr):
        cr.execute("""
            create or replace view report_turnover_per_product as (
                select min(am.id) as id, sum(credit) as turnover,am.product_id as product_id 
                from account_move_line am                    
                group by am.product_id
            )
        """)
report_turnover_per_product()

class report_sale_order_created(osv.osv):
    _name = "report.sale.order.created"
    _description = "Report of Created Sale Order"
    _auto = False
    _columns = {
        'date_order':fields.date('Date Ordered', readonly=True),
        'name': fields.char('Order Reference', size=64, readonly=True),
        'partner_id':fields.many2one('res.partner', 'Customer', readonly=True),
        'partner_shipping_id':fields.many2one('res.partner.address', 'Shipping Address', readonly=True),
        'amount_untaxed': fields.float('Untaxed Amount', readonly=True),
        'state': fields.selection([
            ('draft','Quotation'),
            ('waiting_date','Waiting Schedule'),
            ('manual','Manual In Progress'),
            ('progress','In Progress'),
            ('shipping_except','Shipping Exception'),
            ('invoice_except','Invoice Exception'),
            ('done','Done'),
            ('cancel','Cancel')
            ], 'Order State', readonly=True),
        'create_date' : fields.datetime('Create Date', readolnly=True)
    }
    _order = 'create_date'
    
    def init(self, cr):
        cr.execute("""create or replace view report_sale_order_created as (
            select
                sale.id as id, sale.date_order as date_order, sale.name as name,
                sale.partner_id as partner_id, 
                sale.partner_shipping_id as partner_shipping_id,
                sale.amount_untaxed as amount_untaxed, sale.state as state,
                sale.create_date as create_date
            from
                sale_order sale
            where
                (to_date(to_char(sale.create_date, 'YYYY-MM-dd'),'YYYY-MM-dd') <= CURRENT_DATE)
                AND
                (to_date(to_char(sale.create_date, 'YYYY-MM-dd'),'YYYY-MM-dd') > (CURRENT_DATE-15))
            )""")
report_sale_order_created()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

