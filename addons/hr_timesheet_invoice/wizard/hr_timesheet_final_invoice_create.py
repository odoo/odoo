# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        'group_by_partner': fields.boolean('Group by Partner', help="If this box is checked, the system will group invoices by customer."),
    }

    def do_create(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        # hack for fixing small issue (context should not propagate implicitly between actions)
        if 'default_type' in context:
            del context['default_type']
        ids = self.pool.get('account.analytic.line').search(cr, uid, [('invoice_id','=',False),('to_invoice','<>', False), ('account_id', 'in', context['active_ids'])], context=context)
        invs = self.pool.get('account.analytic.line').invoice_cost_create(cr, uid, ids, data, context=context)
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        mod_ids = mod_obj.search(cr, uid, [('name', '=', 'action_invoice_tree1')], context=context)[0]
        res_id = mod_obj.read(cr, uid, mod_ids, ['res_id'], context=context)['res_id']
        act_win = act_obj.read(cr, uid, [res_id], context=context)[0]
        act_win['domain'] = [('id','in',invs),('type','=','out_invoice')]
        act_win['name'] = _('Invoices')
        return act_win
