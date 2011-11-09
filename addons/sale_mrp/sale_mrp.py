# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

class mrp_production(osv.osv):
    _inherit = 'mrp.production'

    def _ref_calc(self, cr, uid, ids, field_names=None, arg=False, context=None):
        """ Finds reference of sales order for production order.
        @param field_names: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        if not field_names:
            field_names = []
        for id in ids:
            res[id] = {}.fromkeys(field_names, False)
        for f in field_names:
            field_name = False
            if f == 'sale_name':
                field_name = 'name'
            if f == 'sale_ref':
                field_name = 'client_order_ref'
            for key, value in self._get_sale_ref(cr, uid, ids, field_name).items():
                res[key][f] = value
        return res

    def _get_sale_ref(self, cr, uid, ids, field_name=False):
        move_obj = self.pool.get('stock.move')

        def get_parent_move(move_id):
            move = move_obj.browse(cr, uid, move_id)
            if move.move_dest_id:
                return get_parent_move(move.move_dest_id.id)
            return move_id

        res = {}
        productions = self.browse(cr, uid, ids)
        for production in productions:
            res[production.id] = False
            if production.move_prod_id:
                parent_move_line = get_parent_move(production.move_prod_id.id)
                if parent_move_line:
                    move = move_obj.browse(cr, uid, parent_move_line)
                    if field_name == 'name':
                        res[production.id] = move.sale_line_id and move.sale_line_id.order_id.name or False
                    if field_name == 'client_order_ref':
                        res[production.id] = move.sale_line_id and move.sale_line_id.order_id.client_order_ref or False
        return res

    _columns = {
        'sale_name': fields.function(_ref_calc, multi='sale_name', type='char', string='Sales Name', help='Indicate the name of sales order.'),
        'sale_ref': fields.function(_ref_calc, multi='sale_name', type='char', string='Sales Reference', help='Indicate the Customer Reference from sales order.'),
    }

mrp_production()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
