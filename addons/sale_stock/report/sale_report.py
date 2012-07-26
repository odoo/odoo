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
 
from osv import fields, osv
import tools
class sale_report(osv.osv):
     _inherit = "sale.report"
     _columns = {
             'shipped': fields.boolean('Shipped', readonly=True),
             'shipped_qty_1': fields.integer('Shipped', readonly=True),
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
     
     def init(self, cr):
         tools.drop_view_if_exists(cr, 'sale_report')
         cr.execute("""
             create or replace view sale_report as (
                 select
                     min(l.id) as id,
                     l.product_id as product_id,
                     t.uom_id as product_uom,
                     sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
                     sum(l.product_uom_qty * l.price_unit * (100.0-l.discount) / 100.0) as price_total,
                     1 as nbr,
                     s.date_order as date,
                     s.date_confirm as date_confirm,
                     to_char(s.date_order, 'YYYY') as year,
                     to_char(s.date_order, 'MM') as month,
                     to_char(s.date_order, 'YYYY-MM-DD') as day,
                     s.partner_id as partner_id,
                     s.user_id as user_id,
                     s.shop_id as shop_id,
                     s.company_id as company_id,
                     extract(epoch from avg(date_trunc('day',s.date_confirm)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
                     s.state,
                     t.categ_id as categ_id,
                     s.shipped,
                     s.shipped::integer as shipped_qty_1,
                     s.pricelist_id as pricelist_id,
                     s.project_id as analytic_account_id
                 from
                     sale_order s
                     left join sale_order_line l on (s.id=l.order_id)
                         left join product_product p on (l.product_id=p.id)
                             left join product_template t on (p.product_tmpl_id=t.id)
                     left join product_uom u on (u.id=l.product_uom)
                     left join product_uom u2 on (u2.id=t.uom_id)
                 group by
                     l.product_id,
                     l.product_uom_qty,
                     l.order_id,
                     t.uom_id,
                     t.categ_id,
                     s.date_order,
                     s.date_confirm,
                     s.partner_id,
                     s.user_id,
                     s.shop_id,
                     s.company_id,
                     s.state,
                     s.shipped,
                     s.pricelist_id,
                     s.project_id
             )
         """)
sale_report()
