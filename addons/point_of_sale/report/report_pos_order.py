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

class report_pos_order(osv.osv):
    _name = "report.pos.order"
    _description = "Point of Sale Orders Statistics"
    _auto = False
    _columns ={
        'date': fields.date('Date Order', readonly=True),
        'date_validation': fields.date('Date Confirm', readonly=True),
        'date_payment': fields.date('Date Confirm', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('payment', 'Payment'),
                                    ('advance','Advance'),
                                   ('paid', 'Paid'), ('done', 'Done'), ('invoiced', 'Invoiced'), ('cancel', 'Cancel')],
                                  'State'),
        'user_id':fields.many2one('res.users', 'Salesman', readonly=True),
        'price_total':fields.float('Total Price', readonly=True),
        'shop_id':fields.many2one('sale.shop', 'Shop', readonly=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'nbr':fields.integer('# of Lines', readonly=True),
        'product_qty':fields.float('# of Qty', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal'),
    }
    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_pos_order')
        cr.execute("""
            create or replace view report_pos_order as (
                select el.*,

                    (select 1) as nbr,
                    to_date(to_char(po.date_order, 'dd-MM-YYYY'),'dd-MM-YYYY') as date,
                    po.date_validation as date_validation,
                    po.date_payment as date_payment,
                    to_char(po.date_order, 'YYYY') as year,
                    to_char(po.date_order, 'MM') as month,
                    to_char(po.date_order, 'YYYY-MM-DD') as day,
                    po.partner_id as partner_id,
                    po.state as state,
                    po.user_id as user_id,
                    po.shop_id as shop_id,
                    po.company_id as company_id,
                    po.sale_journal as journal_id

                from
                    pos_order as po,
                    ( select pl.id as id,
                        pl.product_id as product_id,
                        pl.qty as product_qty,
                        sum(pl.qty * pl.price_unit)- sum(pl.qty * pl.price_ded) as price_total,
                        pl.order_id
                    from
                        pos_order_line as pl
                        left join product_template pt on (pt.id=pl.product_id)
                    group by
                        pl.id,pl.order_id, pl.qty,pl.product_id)  el
                where po.id = el.order_id
                )
            """)

report_pos_order()
