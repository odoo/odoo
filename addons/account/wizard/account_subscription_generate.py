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

import time

from osv import fields, osv

class account_subscription_generate(osv.osv_memory):

    _name = "account.subscription.generate"
    _description = "Subscription Compute"
    _columns = {
       'date': fields.date('Generate Entries Before', required=True),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
    }
    def action_generate(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        moves_created=[]
        for data in  self.read(cr, uid, ids, context=context):
            cr.execute('select id from account_subscription_line where date<%s and move_id is null', (data['date'],))
            line_ids = map(lambda x: x[0], cr.fetchall())
            moves = self.pool.get('account.subscription.line').move_create(cr, uid, line_ids, context=context)
            moves_created.extend(moves)
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_move_line_form')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = str([('id','in',moves_created)])
        return result

account_subscription_generate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: