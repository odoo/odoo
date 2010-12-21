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
import netsvc
from osv import fields,osv


# Overloaded sale_order to manage carriers :
class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'carrier_id':fields.many2one("delivery.carrier", "Delivery Method", help="Complete this field if you plan to invoice the shipping based on picking."),
        'id': fields.integer('ID', readonly=True,invisible=True),
    }

    def onchange_partner_id(self, cr, uid, ids, part):
        result = super(sale_order, self).onchange_partner_id(cr, uid, ids, part)
        if part:
            dtype = self.pool.get('res.partner').browse(cr, uid, part).property_delivery_carrier.id
            result['value']['carrier_id'] = dtype
        return result

    def action_ship_create(self, cr, uid, ids, *args):
        result = super(sale_order, self).action_ship_create(cr, uid, ids, *args)
        for order in self.browse(cr, uid, ids, context={}):
            pids = [ x.id for x in order.picking_ids]
            self.pool.get('stock.picking').write(cr, uid, pids, {
                'carrier_id':order.carrier_id.id,
            })
        return result
sale_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

