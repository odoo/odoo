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

from openerp import netsvc
from openerp.osv import fields, osv

class make_invoice(osv.osv_memory):
    _name = 'mrp.repair.make_invoice'
    _description = 'Make Invoice'

    _columns = {
           'group': fields.boolean('Group by partner invoice address'),
    }

    def make_invoices(self, cr, uid, ids, context=None):
        """ Generates invoice(s) of selected records.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return: Loads the view of new invoice(s).
        """
        if context is None:
            context = {}
        inv = self.browse(cr, uid, ids[0], context=context)
        order_obj = self.pool.get('mrp.repair')
        mod_obj = self.pool.get('ir.model.data')
        newinv = order_obj.action_invoice_create(cr, uid, context['active_ids'],
                                                 group=inv.group,context=context)

        # We have to trigger the workflow of the given repairs, otherwise they remain 'to be invoiced'.
        # Note that the signal 'action_invoice_create' will trigger another call to the method 'action_invoice_create',
        # but that second call will not do anything, since the repairs are already invoiced.
        wf_service = netsvc.LocalService("workflow")
        for repair_id in context['active_ids']:
            wf_service.trg_validate(uid, 'mrp.repair', repair_id, 'action_invoice_create', cr)

        form_res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        form_id = form_res and form_res[1] or False
        tree_res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_tree')
        tree_id = tree_res and tree_res[1] or Fals

        return {
            'domain': [('id','in', newinv.values())],
            'name': 'Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'views': [(tree_id, 'tree'),(form_id, 'form')],
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window'
        }

make_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

