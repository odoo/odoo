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

from openerp.osv import osv, fields


class stock_return_picking(osv.osv_memory):
    _inherit = 'stock.return.picking'
    _columns = {
        'invoice_state': fields.selection([(
            '2binvoiced', 'To be refunded/invoiced'),
            ('none', 'No invoicing')], 'Invoicing', required=True,
            help="Choose if you want to invoice return stock picking"),
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_return_picking, self).default_get(
            cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        if pick:
            if 'invoice_state' in fields:
                if pick.invoice_state == 'invoiced':
                    res.update({'invoice_state': '2binvoiced'})
                else:
                    res.update({'invoice_state': 'none'})
        return res

    def _create_returns(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids[0], context=context)
        new_picking, picking_type_id = super(stock_return_picking, self).\
            _create_returns(cr, uid, ids, context=context)

        pick_obj = self.pool.get("stock.picking")
        move_obj = self.pool.get("stock.move")
        move_ids = [x.id for x in pick_obj.browse(
            cr, uid, new_picking, context=context).move_lines]

        if data.invoice_state == '2binvoiced':
            move_obj.write(cr, uid, move_ids, {'invoice_state': '2binvoiced'})
        elif data.invoice_state == 'none':
            move_obj.write(cr, uid, move_ids, {'invoice_state': 'none'})
        return new_picking, picking_type_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
