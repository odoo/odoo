# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MakeInvoice(models.TransientModel):
    _name = 'repair.order.make_invoice'
    _description = 'Create Mass Invoice (repair)'

    group = fields.Boolean('Group by partner invoice address')

    @api.multi
    def make_invoices(self):
        if not self._context.get('active_ids'):
            return {'type': 'ir.actions.act_window_close'}
        new_invoice = {}
        for wizard in self:
            repairs = self.env['repair.order'].browse(self._context['active_ids'])
            new_invoice = repairs.action_invoice_create(group=wizard.group)

            # We have to udpate the state of the given repairs, otherwise they remain 'to be invoiced'.
            # Note that this will trigger another call to the method 'action_invoice_create',
            # but that second call will not do anything, since the repairs are already invoiced.
            repairs.action_repair_invoice_create()
        return {
            'domain': [('id', 'in', list(new_invoice.values()))],
            'name': 'Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'views': [(self.env.ref('account.invoice_tree').id, 'tree'), (self.env.ref('account.invoice_form').id, 'form')],
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window'
        }
