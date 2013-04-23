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

from openerp.osv import fields, osv
from openerp.tools.translate import _

#
# Create an final invoice based on selected timesheet lines
#

#
# TODO: check unit of measure !!!
#
class final_invoice_create(osv.osv_memory):
    _name = 'hr.timesheet.invoice.create.final'
    _description = 'Create invoice from timesheet final'
    _columns = {
        'date': fields.boolean('Date', help='Display date in the history of works'),
        'time': fields.boolean('Time Spent', help='Display time in the history of works'),
        'name': fields.boolean('Log of Activity', help='Display detail of work in the invoice line.'),
        'price': fields.boolean('Cost', help='Display cost of the item you reinvoice'),
        'product': fields.many2one('product.product', 'Product', help='The product that will be used to invoice the remaining amount'),
    }

    def do_create(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        # hack for fixing small issue (context should not propagate implicitly between actions)
        if 'default_type' in context:
            del context['default_type']
        ids = self.pool.get('account.analytic.line').search(cr, uid, [('invoice_id','=',False),('to_invoice','<>', False), ('account_id', 'in', context['active_ids'])], context=context)
        invs = self.pool.get('account.analytic.line').invoice_cost_create(cr, uid, ids, data, context=context)
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        mod_ids = mod_obj.search(cr, uid, [('name', '=', 'action_invoice_tree1')], context=context)[0]
        res_id = mod_obj.read(cr, uid, mod_ids, ['res_id'], context=context)['res_id']
        act_win = act_obj.read(cr, uid, res_id, [], context=context)
        act_win['domain'] = [('id','in',invs),('type','=','out_invoice')]
        act_win['name'] = _('Invoices')
        return act_win

final_invoice_create()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
