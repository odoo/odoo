# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tests.common import Form


class ImportInvoiceImportWizard(models.TransientModel):
    _name = 'account.invoice.import.wizard'
    _description = 'Import Your Vendor Bills from Files.'

    def _get_default_journal_id(self):
        return self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)

    attachment_ids = fields.Many2many('ir.attachment', string='Files')
    journal_id = fields.Many2one(string="Journal", comodel_name="account.journal", required=True, domain="[('type', '=', 'purchase')]", default=_get_default_journal_id, help="Journal where to generate the bills")

    @api.multi
    def _create_invoice_from_file(self, attachment):
        self = self.with_context(default_journal_id= self.journal_id.id)
        invoice_form = Form(self.env['account.invoice'], view='account.invoice_supplier_form')
        invoice = invoice_form.save()
        attachment.write({'res_model': 'account.invoice', 'res_id': invoice.id})
        invoice.message_post(attachment_ids=[attachment.id])
        return invoice

    @api.multi
    def create_invoices(self):
        ''' Create the invoices from files.
         :return: A action redirecting to account.invoice tree/form view.
        '''
        if not self.attachment_ids:
            return

        invoices = self.env['account.invoice']
        for attachment in self.attachment_ids:
            invoices += self._create_invoice_from_file(attachment)

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
