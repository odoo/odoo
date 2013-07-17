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


from openerp.osv import fields, osv
from openerp.tools.translate import _

class hr_timesheet_invoice_create(osv.osv_memory):

    _name = 'hr.timesheet.invoice.create'
    _description = 'Create invoice from timesheet'
    _columns = {
        'date': fields.boolean('Date', help='The real date of each work will be displayed on the invoice'),
        'time': fields.boolean('Time spent', help='The time of each work done will be displayed on the invoice'),
        'name': fields.boolean('Description', help='The detail of each work done will be displayed on the invoice'),
        'price': fields.boolean('Cost', help='The cost of each work done will be displayed on the invoice. You probably don\'t want to check this'),
        'product': fields.many2one('product.product', 'Force Product', help='Fill this field only if you want to force to use a specific product. Keep empty to use the real product that comes from the cost.'),
    }

    _defaults = {
         'date':  1,
         'name':  1,
    }

    def view_init(self, cr, uid, fields, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values
        """
        analytic_obj = self.pool.get('account.analytic.line')
        data = context and context.get('active_ids', [])
        for analytic in analytic_obj.browse(cr, uid, data, context=context):
            if analytic.invoice_id:
                raise osv.except_osv(_('Warning!'), _("Invoice is already linked to some of the analytic line(s)!"))

    def do_create(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        # Create an invoice based on selected timesheet lines
        invs = self.pool.get('account.analytic.line').invoice_cost_create(cr, uid, context['active_ids'], data, context=context)
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        mod_ids = mod_obj.search(cr, uid, [('name', '=', 'action_invoice_tree1')], context=context)[0]
        res_id = mod_obj.read(cr, uid, mod_ids, ['res_id'], context=context)['res_id']
        act_win = act_obj.read(cr, uid, res_id, [], context=context)
        act_win['domain'] = [('id','in',invs),('type','=','out_invoice')]
        act_win['name'] = _('Invoices')
        return act_win


hr_timesheet_invoice_create()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

