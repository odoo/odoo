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


class report_stock_move(osv.osv):
    _name = "report.stock.move"
    _description = "Stock Statistics"
    _auto = False
    _columns = {
        'date': fields.date('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'location_id': fields.many2one('stock.location', 'Source Location', readonly=True, select=True, help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations."),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', readonly=True, select=True, help="Location where the system will stock the finished products."),
        'product_qty':fields.integer('Qty',readonly=True),
        'product_uom': fields.many2one('product.uom', 'Product UOM', readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('waiting', 'Waiting'), ('confirmed', 'Confirmed'), ('assigned', 'Available'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, select=True,
                                  help='When the stock move is created it is in the \'Draft\' state.\n After that it is set to \'Confirmed\' state.\n If stock is available state is set to \'Avaiable\'.\n When the picking it done the state is \'Done\'.\
                                  \nThe state is \'Waiting\' if the move is waiting for another one.'),

    }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_move')
        cr.execute("""
            create or replace view report_stock_move as (
                select min(m.id) as id,
                m.date as date,
                to_char(date_trunc('day',m.date), 'YYYY') as year,
                to_char(date_trunc('day',m.date), 'MM') as month,
                to_char(date_trunc('day',m.date), 'YYYY-MM-DD') as day,
                m.location_id as location_id,
                m.location_dest_id as location_dest_id,
                m.product_id as product_id,
                m.state as state,
                m.product_uom as product_uom,
                sum(m.product_qty) as product_qty
                from stock_move as m group by m.id, m.product_id, m.location_id, m.location_dest_id, m.date, m.state, m.product_uom
            )
        """)
report_stock_move()
