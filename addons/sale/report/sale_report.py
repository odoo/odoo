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
from osv import fields, osv

class sale_report(osv.osv):
    _name = "sale.report"
    _description = "Sales Orders Statistics"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Date Order', readonly=True),
        'date_confirm': fields.date('Date Confirm', readonly=True),
        'shipped': fields.boolean('Shipped', readonly=True),
        'shipped_qty_1': fields.integer('Shipped', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month': fields.selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
            ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'), ('09', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'uom_name': fields.char('Reference UoM', size=128, readonly=True),
        'product_uom_qty': fields.float('# of Qty', readonly=True),

        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'shop_id': fields.many2one('sale.shop', 'Shop', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesman', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'delay': fields.float('Commitment Delay', digits=(16,2), readonly=True),
        'categ_id': fields.many2one('product.category','Category of Product', readonly=True),
        'nbr': fields.integer('# of Lines', readonly=True),
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
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', readonly=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
    }
    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'sale_report')
        cr.execute("""
            create or replace view sale_report as (
                select el.*,
                   -- (select count(1) from sale_order_line where order_id = s.id) as nbr,
                    (select 1) as nbr,
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
                     s.shipped,
                     s.shipped::integer as shipped_qty_1,
                     s.pricelist_id as pricelist_id,
                     s.project_id as analytic_account_id
                from
                sale_order s,
                    (
                    select l.id as id,
                        l.product_id as product_id,
                        (case when u.uom_type not in ('reference') then
                            (select name from product_uom where uom_type='reference' and category_id=u.category_id)
                        else
                            u.name
                        end) as uom_name,
                        sum(l.product_uom_qty / u.factor) as product_uom_qty,
                        sum(l.product_uom_qty * l.price_unit) as price_total,
                        pt.categ_id, l.order_id
                    from
                     sale_order_line l ,product_uom u, product_product p, product_template pt
                     where u.id = l.product_uom
                     and pt.id = p.product_tmpl_id
                     and p.id = l.product_id
                      group by l.id, l.order_id, l.product_id, u.name, pt.categ_id, u.uom_type, u.category_id) el
                where s.id = el.order_id
                group by el.id,
                    el.product_id,
                    el.uom_name,
                    el.product_uom_qty,
                    el.price_total,
                    el.categ_id,
                    el.order_id,
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
