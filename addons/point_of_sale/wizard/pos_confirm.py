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
from osv import osv


class pos_confirm(osv.osv_memory):
    _name = 'pos.confirm'
    _description = 'Point of Sale Confirm'

    def action_confirm(self, cr, uid, ids, context=None):
        """
             Confirm the order and close the sales.
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return :Blank dictionary
        """
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False)
        if record_id:
            if isinstance(record_id, (int, long)):
                record_id = [record_id]
            if record_id:
                order_obj = self.pool.get('pos.order')

                for order_id in order_obj.browse(cr, uid, record_id, context=context):
                    if  order_id.state == 'paid':
                        order_obj.write(cr, uid, [order_id.id], {'journal_entry': True}, context=context)
                        order_obj.create_account_move(cr, uid, [order_id.id], context=context)

                wf_service = netsvc.LocalService("workflow")
                for i in record_id:
                    wf_service.trg_validate(uid, 'pos.order', i, 'done', cr)
        return {}

pos_confirm()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

