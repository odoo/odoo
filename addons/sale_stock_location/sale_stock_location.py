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
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from dateutil.relativedelta import relativedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _


class sale_order(osv.osv):
    _inherit = "sale.order"
    
    
    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
        '''
            Add route_ids to the procurement.  As such, people should choose between them. 
        '''
        res = super(sale_order, self)._prepare_order_line_procurement(cr, uid, order, line, group_id=group_id, context=context)
        routes = []
        route_id = order.warehouse_id and order.warehouse_id.route_id and order.warehouse_id.route_id.id or False
        routes += route_id and [(4, route_id)] or []
        route_id = line.route_id and line.route_id.id or False
        routes += route_id and [(4, route_id)] or []
        res.update({
                'route_ids': routes
                })
        return res

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    _columns = { 
        'route_id': fields.many2one('stock.location.route', 'Route', domain=[('sale_selectable', '=', True)]),
    }


class stock_location_route(osv.osv):
    _inherit = "stock.location.route"
    _columns = {
        'sale_selectable':fields.boolean("Selectable on Sales Order Line")
        }



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
