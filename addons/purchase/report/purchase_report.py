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

#
# Please note that these reports are not multi-currency !!!
#

from osv import fields,osv
import tools

class report_purchase_order(osv.osv):
    _name = "purchase.report"
    _description = "Purchases Orders"
    _auto = False
    _columns = {
        'date': fields.date('Date', readonly=True),
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
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', readonly=True),
        'category_id': fields.many2one('product.category', 'Categories', readonly=True),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'user_id':fields.many2one('res.users', 'Responsible', readonly=True),
        'quantity': fields.float('# of Products', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'price_average': fields.float('Average Price', readonly=True),
        'nbr': fields.integer('# of Lines', readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                          ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),

    }
    _order = 'name desc,price_total desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'purchase_report')
        cr.execute("""
            create or replace view purchase_report as (
                select
                    min(l.id) as id,
                    s.date_order as date,
                    to_char(s.date_order, 'YYYY') as name,
                    to_char(s.date_order, 'MM') as month,
                    s.state,
                    s.warehouse_id as warehouse_id,
                    s.partner_id as partner_id,
                    s.create_uid as user_id,
                    s.company_id as company_id,
                    l.product_id,
                    t.categ_id as category_id,
                    sum(l.product_qty*u.factor) as quantity,
                    count(*) as nbr,
                    sum(l.product_qty*l.price_unit) as price_total,
                    (sum(l.product_qty*l.price_unit)/sum(l.product_qty*u.factor))::decimal(16,2) as price_average
                from purchase_order s
                    left join purchase_order_line l on (s.id=l.order_id)
                    left join product_product p on (p.id=l.product_id)
                    left join product_template t on (t.id=p.product_tmpl_id)
                    left join product_uom u on (u.id=l.product_uom)
                where l.product_id is not null
                group by s.company_id,s.create_uid,s.partner_id,
                         t.categ_id,l.product_id,s.date_order,
                         to_char(s.date_order, 'YYYY'),to_char(s.date_order, 'MM'),s.state,
                         s.warehouse_id
            )
        """)
report_purchase_order()

class purchase_order_qty_amount(osv.osv):
    _name = "purchase.order.qty.amount"
    _description = "Quantity and amount per month"
    _auto = False
    _columns = {
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                          ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
        'total_qty' : fields.float('Total Qty'),
        'total_amount' : fields.float('Total Amount'),

        }
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'purchase_order_qty_amount')
        cr.execute("""
            create or replace view purchase_order_qty_amount as (
                select
                    min(id) as id,
                    to_char(create_date, 'MM') as month,
                    sum(product_qty) as total_qty,
                    sum(price_unit) as total_amount
                from
                    purchase_order_line
                where
                    to_char(create_date,'YYYY') =  to_char(current_date,'YYYY')
                group by
                    to_char(create_date, 'MM')

            )
        """)
purchase_order_qty_amount()

class purchase_order_by_user(osv.osv):
    _name = "purchase.order.by.user"
    _description = "Purchase Order by user per month"
    _auto = False
    _columns = {
        'name' : fields.char('User',size=64,required=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                          ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
        'nbr' : fields.integer('Total Orders'),

        }
    _order = 'name desc'
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'purchase_order_by_user')
        cr.execute("""
            create or replace view purchase_order_by_user as (
                select
                    min(po.id) as id,
                    rs.name as name,
                    count(po.id) as nbr,
                    to_char(po.date_order, 'MM') as month
                from
                    purchase_order as po,res_users as rs
                where
                    po.create_uid = rs.id
                group by
                    rs.name,po.date_order

            )
        """)
purchase_order_by_user()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

