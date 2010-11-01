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

from osv import osv, fields
from tools.translate import _


class pos_get_sale(osv.osv_memory):
    _name = 'pos.get.sale'
    _description = 'Get From Sale'

    _columns = {
        'picking_id': fields.many2one('stock.picking', 'Sale Order', domain=[('state', 'in', ('assigned', 'confirmed')), ('type', '=', 'out')], context="{'contact_display': 'partner'}", required=True),
    }

    def sale_complete(self, cr, uid, ids, context=None):
        """
             Select the picking order and add the in Point of sale order
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : nothing
        """
        proxy_pos = self.pool.get('pos.order')
        proxy_pick = self.pool.get('stock.picking')
        proxy_order_line = self.pool.get('pos.order.line')
        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0], context=context)
        record_id = context and context.get('active_id', False)

        if record_id:
            order = proxy_pos.browse(cr, uid, record_id, context=context)
            if order.state in ('paid', 'invoiced'):
                raise osv.except_osv(_('UserError '), _("You can't modify this order. It has already been paid"))

            for pick in proxy_pick.browse(cr, uid, [this.picking_id.id], context=context):
                proxy_pos.write(cr, uid, record_id, {
                    'picking_id': this.picking_id.id,
                    'partner_id': pick.address_id and pick.address_id.partner_id.id
                }, context=context)

            order = proxy_pick.write(cr, uid, [this.picking_id.id], {
                                        'invoice_state': 'none',
                                        'pos_order': record_id
                                    }, context=context)

            for line in pick.move_lines:
                proxy_order_line.create(cr, uid, {
                    'name': line.sale_line_id.name,
                    'order_id': record_id,
                    'qty': line.product_qty,
                    'product_id': line.product_id.id,
                    'price_unit': line.sale_line_id.price_unit,
                    'discount': line.sale_line_id.discount,
                }, context=context)
        return {}

pos_get_sale()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

