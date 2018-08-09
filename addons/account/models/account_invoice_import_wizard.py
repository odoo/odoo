# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tests.common import Form


class ImportInvoiceImportWizard(models.TransientModel):
    _name = 'account.invoice.import.wizard'
    _description = 'Import Your Vendor Bills from Files.'

    attachment_ids = fields.Many2many('ir.attachment', string='Files')

    @api.multi
    def _create_invoice_from_file(self, attachment):
        invoice_form = Form(self.env['account.invoice'], view='account.invoice_supplier_form')
        invoice = invoice_form.save()
        invoice.message_post(attachment_ids=[attachment.id])
        return invoice

    @api.multi
    def create_invoices(self):
        ''' Create the invoices from files.
         :return: A action redirecting to account.invoice tree/form view.
        '''
        if not self.attachment_ids:
            return

        # type/journal_id must be inside the context to get the right behavior of _default_journal
        self_ctx = self.with_context(type='in_invoice')
        journal_id = self_ctx._default_journal().id
        self_ctx = self_ctx.with_context(journal_id=journal_id)

        invoices = self.env['account.invoice']
        for attachment in self.attachment_ids:
            invoices +=self_ctx._create_invoice_from_file(attachment)

        action_vals = {
            'name': _('Invoices'),
            'domain': [('id', 'in', invoices.ids)],
            'view_type': 'form',
            'res_model': 'account.invoice',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        if len(invoices) == 1:
            action_vals.update({'res_id': invoices[0].id, 'view_mode': 'form'})
        else:
            action_vals['view_mode'] = 'tree,form'
        return action_vals
