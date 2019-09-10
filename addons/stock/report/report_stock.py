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

from openerp.osv import fields, osv
from openerp.tools.sql import drop_view_if_exists

class report_stock_lines_date(osv.osv):
    _name = "report.stock.lines.date"
    _description = "Dates of Inventories and latest Moves"
    _auto = False
    _order = "date"
    _columns = {
        'id': fields.integer('Product Id', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True, select=True),
        'date': fields.datetime('Date of latest Inventory', readonly=True),
        'move_date': fields.datetime('Date of latest Stock Move', readonly=True),
        "active": fields.boolean("Active", readonly=True),
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'report_stock_lines_date')
        cr.execute("""
            create or replace view report_stock_lines_date as (
                select
                p.id as id,
                p.id as product_id,
                max(s.date) as date,
                max(m.date) as move_date,
                p.active as active
            from
                product_product p
                    left join (
                        stock_inventory_line l
                        inner join stock_inventory s on (l.inventory_id=s.id and s.state = 'done')
                    ) on (p.id=l.product_id)
                    left join stock_move m on (m.product_id=p.id and m.state = 'done')
                group by p.id
            )""")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
