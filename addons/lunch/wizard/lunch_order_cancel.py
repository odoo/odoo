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

class lunch_order_cancel(osv.osv_memory):
    """
    Cancel Lunch Order
    """
    _name = "lunch.order.cancel"
    _description = "Cancel Order"

    def cancel(self, cr, uid, ids, context=None):
        """
        Cancel cashmove entry from cashmoves and update state to draft.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List  Lunch Order Cancel’s IDs
        """
        if context is None:
            context = {}
        data = context and context.get('active_ids', []) or []
        return self.pool.get('lunch.order').lunch_order_cancel(cr, uid, data, context)

lunch_order_cancel()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

