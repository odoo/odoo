# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class hr_timesheet_invoice_create(osv.osv_memory):

    _name = 'hr.timesheet.invoice.create'
    _description = 'Create invoice from timesheet'
    _columns = {
        'date': fields.boolean('Date', help='The real date of each work will be displayed on the invoice'),
        'time': fields.boolean('Time spent', help='The time of each work done will be displayed on the invoice'),
        'name': fields.boolean('Description', help='The detail of each work done will be displayed on the invoice'),
        'price': fields.boolean('Cost', help='The cost of each work done will be displayed on the invoice. You probably don\'t want to check this'),
        'product': fields.many2one('product.product', 'Force Product', help='Fill this field only if you want to force the use a specific product. Keep empty to use the real product that comes from the cost.'),
        'group_by_partner': fields.boolean('Group by Partner', help='If this box is checked, the system will group invoices by customer.'),
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
        data = context and context.get('active_ids', []) or []
        for analytic in analytic_obj.browse(cr, uid, data, context=context):
            if analytic.invoice_id:
                raise UserError(_("Invoice is already linked to some of the analytic line(s)!"))

    def do_create(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        # Create an invoice based on selected timesheet lines
        invs = self.pool.get('account.analytic.line').invoice_cost_create(cr, uid, context['active_ids'], data, context=context)
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        mod_ids = mod_obj.search(cr, uid, [('name', '=', 'action_invoice_tree1')], context=context)
        res_id = mod_obj.read(cr, uid, mod_ids, ['res_id'], context=context)[0]['res_id']
        act_win = act_obj.read(cr, uid, [res_id], context=context)[0]
        act_win['domain'] = [('id','in',invs),('type','=','out_invoice')]
        act_win['name'] = _('Invoices')
        return act_win
