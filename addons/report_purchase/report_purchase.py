# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

#
# Please note that these reports are not multi-currency !!!
#

from osv import fields,osv
import tools

class report_purchase_order_product(osv.osv):
    _name = "report.purchase.order.product"
    _description = "Purchases Orders by Products"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
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
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                          ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),

    }
    _order = 'name desc,price_total desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'report_purchase_order_product')
        cr.execute("""
            create or replace view report_purchase_order_product as (
                select
                    min(l.id) as id,
                    to_char(s.date_order, 'YYYY') as name,
                    to_char(s.date_order, 'MM') as month,
                    s.state,
                    l.product_id,
                    sum(l.product_qty*u.factor) as quantity,
                    count(*),
                    sum(l.product_qty*l.price_unit) as price_total,
                    (sum(l.product_qty*l.price_unit)/sum(l.product_qty*u.factor))::decimal(16,2) as price_average
                from purchase_order s
                    left join purchase_order_line l on (s.id=l.order_id)
                    left join product_uom u on (u.id=l.product_uom)
                where l.product_id is not null
                group by l.product_id, to_char(s.date_order, 'YYYY'),to_char(s.date_order, 'MM'),s.state
            )
        """)
report_purchase_order_product()

class report_purchase_order_category(osv.osv):
    _name = "report.purchase.order.category"
    _description = "Purchases Orders by Categories"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
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
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
    }
    _order = 'name desc,price_total desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'report_purchase_order_category')
        cr.execute("""
            create or replace view report_purchase_order_category as (
                select
                    min(l.id) as id,
                    to_char(s.date_order, 'YYYY') as name,
                    to_char(s.date_order, 'MM') as month,
                    s.state,
                    t.categ_id as category_id,
                    sum(l.product_qty*u.factor) as quantity,
                    count(*),
                    sum(l.product_qty*l.price_unit) as price_total,
                    (sum(l.product_qty*l.price_unit)/sum(l.product_qty*u.factor))::decimal(16,2) as price_average
                from purchase_order s
                    left join purchase_order_line l on (s.id=l.order_id)
                    left join product_product p on (p.id=l.product_id)
                    left join product_template t on (t.id=p.product_tmpl_id)
                    left join product_uom u on (u.id=l.product_uom)
                where l.product_id is not null
                group by t.categ_id, to_char(s.date_order, 'YYYY'),to_char(s.date_order, 'MM'),s.state
             )
        """)
report_purchase_order_category()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

