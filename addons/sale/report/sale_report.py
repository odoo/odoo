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

import tools
from osv import fields,osv


class sale_report(osv.osv):
    _name = "sale.report"
    _description = "Sales Orders Statistics"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'product_qty':fields.float('Qty', readonly=True),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True),
        'shop_id':fields.many2one('sale.shop', 'Shop', readonly=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'user_id':fields.many2one('res.users', 'Salesman', readonly=True),
        'price_total':fields.float('Total Price', readonly=True),
        'delay':fields.float('Avg Closing Days', digits=(16,2), readonly=True),
        'price_average':fields.float('Average Price', readonly=True),
        'nbr':fields.integer('# of Lines', readonly=True),
        'state': fields.selection([
            ('draft', 'Quotation'),
            ('waiting_date', 'Waiting Schedule'),
            ('manual', 'Manual In Progress'),
            ('progress', 'In Progress'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ('cancel', 'Cancelled')
            ], 'Order State', readonly=True),
    }
    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'sale_report')
        cr.execute("""
            create or replace view sale_report as (
                 select
                     min(l.id) as id,
                     s.date_order as date,
                     to_char(s.date_order, 'YYYY') as year,
                     to_char(s.date_order, 'MM') as month,
                     l.product_id as product_id,
                     sum(l.product_uom_qty * u.factor) as product_qty,
                     s.partner_id as partner_id,
                     s.user_id as user_id,
                     s.shop_id as shop_id,
                     s.company_id as company_id,
                     extract(epoch from avg(s.date_confirm-s.create_date))/(24*60*60)::decimal(16,2) as delay,
                     sum(l.product_uom_qty*l.price_unit) as price_total,
                     (sum(l.product_uom_qty*l.price_unit)/sum(l.product_uom_qty * u.factor))::decimal(16,2) as price_average,
                     count(*) as nbr,
                     s.state
                     from
                 sale_order_line l
                 left join
                     sale_order s on (s.id=l.order_id)
                     left join product_uom u on (u.id=l.product_uom)
                 group by
                     s.date_order, s.partner_id, l.product_id,
                     l.product_uom, s.user_id, s.state, s.shop_id,
                     s.company_id
            )
        """)
sale_report()

class sale_order_by_clients(osv.osv):
    _name = "sale.order.by.clients"
    _description = "Sales order by clients"
    _auto = False
    _rec_name = 'partner'
    _columns = {
        'total_orders': fields.integer('Total'),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True)
    }
    _order = 'total_orders desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'sale_order_by_clients')
        cr.execute("""
            create or replace view sale_order_by_clients as (
                 select
                     min(s.id) as id,
                     count(*) as total_orders,
                     s.partner_id as partner_id
                 from
                      sale_order s
                 where
                    s.state='manual' or s.state='progress'
                 group by
                        s.partner_id
            )
        """)
sale_order_by_clients()

class uninvoiced_lines_per_month(osv.osv):
    _name = "uninvoiced.lines.per.month"
    _description = "Uninvoiced lines per month"
    _auto = False
    _rec_name = 'month'
    _columns = {
        'number_of_lines': fields.integer('Total Lines', readonly=True),
        'year': fields.char('Year', size=10, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),

    }
    _order = 'number_of_lines desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'uninvoiced_lines_per_month')
        cr.execute("""
            create or replace view uninvoiced_lines_per_month as (
                select
                     min(s.id) as id,
                     count(*) as number_of_lines,
                     to_char(s.create_date, 'MM') as month,
                     to_char(s.create_date, 'YYYY') as year
                from
                     sale_order_line s
                where
                     s.state='draft'
                group by
                     to_char(s.create_date, 'MM'),to_char(s.create_date, 'YYYY')
            )
        """)
uninvoiced_lines_per_month()

class product_bought_by_sale_order(osv.osv):
    _name = "product.bought.by.sale.order"
    _description = "Product bought by sale order"
    _auto = False
    _rec_name = 'partner'
    _columns = {
        'total_products': fields.integer('Total Products', readonly=True),
        'name': fields.char('Sale order', size=64, readonly=True)
    }
    _order = 'total_products desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'product_bought_by_sale_order')
        cr.execute("""
            create or replace view product_bought_by_sale_order as (
                select
                    min(s.id) as id,
                    count(*) as total_products,
                    s.name as name
                from
                    sale_order_line l
                left join
                    sale_order s on (s.id=l.order_id)
                where
                    s.state='manual' or s.state='progress'
                group by
                    s.name
            )
        """)
product_bought_by_sale_order()

class sales_by_regions(osv.osv):
    _name = "sales.by.regions"
    _description = "Sales by regions"
    _auto = False
    _rec_name = 'name'
    _columns = {
        'total_sales': fields.integer('Total Sales', readonly=True),
        'name': fields.char('Country', size=64, readonly=True),
    }
    _order = 'total_sales desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'sales_by_regions')
        cr.execute("""
            create or replace view sales_by_regions as (
               select
                   min(s.id) as id,
                   rc.name as name,
                   count(s.name) as total_sales
               from
                   sale_order s,res_partner_address p,res_country rc
               where
                   s.partner_id=p.id and
                   p.country_id=rc.id and
                   (s.state='manual' or s.state='progress')
               group by
                   rc.name
            )
        """)
sales_by_regions()


