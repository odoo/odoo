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
from openerp import tools

class sale_report(osv.osv):
    _inherit = "sale.report"
    _columns = {
        'shipped': fields.boolean('Shipped', readonly=True),
        'shipped_qty_1': fields.integer('Shipped', readonly=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse',readonly=True),
        'state': fields.selection([
            ('draft', 'Quotation'),
            ('waiting_date', 'Waiting Schedule'),
            ('manual', 'Manual In Progress'),
            ('progress', 'In Progress'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ('cancel', 'Cancelled')
            ], 'Order Status', readonly=True),
    }

    def _select(self):
        return  super(sale_report, self)._select() + ", s.warehouse_id as warehouse_id, s.shipped, s.shipped::integer as shipped_qty_1"

    def _group_by(self):
        return super(sale_report, self)._group_by() + ", s.warehouse_id, s.shipped"

