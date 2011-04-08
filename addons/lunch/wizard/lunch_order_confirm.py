# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv

class lunch_order_confirm(osv.osv_memory):
    """
    Confirm Lunch Order
    """
    _name = "lunch.order.confirm"
    _description = "confirm Order"

    _columns = {
        'confirm_cashbox':fields.many2one('lunch.cashbox', 'Name of box', required=True),
    }

    def confirm(self, cr, uid, ids, context=None):
        """
        confirm Lunch Order.Create cashmoves in launch cashmoves when state is
                        confirm in lunch order.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List  Lunch Order confirm’s IDs
        @return: Dictionary {}.
        """
        if context is None:
            context = {}
        data = context and context.get('active_ids', []) or []
        order_ref = self.pool.get('lunch.order')

        for confirm_obj in self.browse(cr, uid, ids, context=context):
            order_ref.confirm(cr, uid, data, confirm_obj.confirm_cashbox.id, context)
            return {'type': 'ir.actions.act_window_close'}

lunch_order_confirm()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

