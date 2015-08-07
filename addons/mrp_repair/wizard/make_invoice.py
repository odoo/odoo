# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class MakeInvoice(models.TransientModel):
    _name = 'mrp.repair.make_invoice'
    _description = 'Make Invoice'

    group = fields.Boolean('Group by partner invoice address')

    @api.multi
    def make_invoices(self):
        """ Generates invoice(s) of selected records.
        @return: Loads the view of new invoice(s).
        """
        orders = self.env['mrp.repair'].browse(self.env.context['active_ids'])
        newinv = orders.action_invoice_create(group=self.group)
        # We have to trigger the workflow of the given repairs, otherwise they remain 'to be invoiced'.
        # Note that the signal 'action_invoice_create' will trigger another call to the method 'action_invoice_create',
        # but that second call will not do anything, since the repairs are already invoiced.
        orders.signal_workflow('action_invoice_create')
        form_res = self.env.ref('account.invoice_form')
        form_id = form_res and form_res.id or False
        tree_res = self.env.ref('account.invoice_tree')
        tree_id = tree_res and tree_res.id or False
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
