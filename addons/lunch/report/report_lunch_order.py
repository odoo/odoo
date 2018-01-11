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

from openerp import tools
from openerp.osv import fields,osv

class report_lunch_order(osv.osv):
    _name = "report.lunch.order.line"
    _description = "Lunch Orders Statistics"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Date Order', readonly=True, select=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'user_id': fields.many2one('res.users', 'User Name'),
        'price_total':fields.float('Total Price', readonly=True),
        'note' : fields.text('Note', readonly=True),
    }
    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_lunch_order_line')
        cr.execute("""
            create or replace view report_lunch_order_line as (
               select
                   min(lo.id) as id,
                   lo.user_id as user_id,
                   lo.date as date,
                   to_char(lo.date, 'YYYY') as year,
                   to_char(lo.date, 'MM') as month,
                   to_char(lo.date, 'YYYY-MM-DD') as day,
                   lo.note as note,
                   sum(lp.price) as price_total

            from
                   lunch_order_line as lo
                   left join lunch_product as lp on (lo.product_id = lp.id)
            group by
                   lo.date,lo.user_id,lo.note
            )
            """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
