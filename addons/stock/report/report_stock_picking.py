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
from osv import fields,osv
import tools

class report_stock_picking(osv.osv):
    _name = "report.stock.picking"
    _description = "Stock Picking Report"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
        'reference': fields.char('Reference', size=64, select=True),
        'nbr': fields.integer('# of Orders', readonly=True),
        'origin': fields.char('Origin', size=64),
        'order_date':fields.date('Order Date'),
        'state': fields.selection([('draft', 'Draft'),('auto', 'Waiting'),('confirmed', 'Confirmed'),('assigned', 'Available'),('done', 'Done'),('cancel', 'Cancelled')], 'State'),
        'type': fields.selection([('out', 'Sending Goods'), ('in', 'Getting Goods'), ('internal', 'Internal'), ('delivery', 'Delivery')], 'Shipping Type', required=True),
        'address_id': fields.many2one('res.partner.address', 'Partner'),
        'expected_date': fields.date('Expected Date'),

    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_picking')
        cr.execute("""
            create or replace view report_stock_picking as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.name as reference,
                    c.origin,
                    c.state,
                    c.type,
                    c.address_id,
                    to_date(to_char(c.date, 'MM-dd-YYYY'),'MM-dd-YYYY') as order_date,
                    to_date(to_char(c.min_date, 'MM-dd-YYYY'),'MM-dd-YYYY') as expected_date,
                    count(*) as nbr
                from
                    stock_picking c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'),c.name,c.origin,c.date,c.state,c.type,c.address_id,c.min_date
            )""")
report_stock_picking()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
