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
    _description = 'Post POS Journal Entries'

    def action_confirm(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        order_obj = self.pool.get('pos.order')
        ids = order_obj.search(cr, uid, [('state','=','paid')], context=context)
        for order in order_obj.browse(cr, uid, ids, context=context):
            todo = True
            for line in order.statement_ids:
                if line.statement_id.state <> 'confirm':
                    todo = False
                    break
            if todo:
                wf_service.trg_validate(uid, 'pos.order', order.id, 'done', cr)
        return {}
pos_confirm()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

