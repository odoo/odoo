# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tests.common import Form
from odoo.exceptions import UserError


class ImportInvoiceImportWizard(models.TransientModel):
    _name = 'account.invoice.import.wizard'
    _description = 'Import Your Vendor Bills from Files.'

    attachment_ids = fields.Many2many('ir.attachment', string='Files')

    def _create_invoice_from_file(self, attachment):
        invoice = self.env['account.move'].create({})
        attachment.write({'res_model': 'account.move', 'res_id': invoice.id})
        invoice.message_post(attachment_ids=[attachment.id])
        return invoice

    def _create_invoice(self, attachment):
        return self._create_invoice_from_file(attachment)

    def create_invoices(self):
        ''' Create the invoices from files.
         :return: A action redirecting to account.invoice tree/form view.
        '''
        if not self.attachment_ids:
            raise UserError(_("No attachment was provided"))

        invoices = self.env['account.move']
        for attachment in self.attachment_ids:
            invoices += self._create_invoice(attachment)

        action_vals = {
            'name': _('Generated Documents'),
            'domain': [('id', 'in', invoices.ids)],
            'view_type': 'form',
            'res_model': 'account.move',
            'views': [[False, "tree"], [False, "form"]],
            'type': 'ir.actions.act_window',
            'context': self.env.context,
        }
        if len(invoices) == 1:
            action_vals.update({'res_id': invoices[0].id, 'view_mode': 'form'})
        else:
            action_vals['view_mode'] = 'tree,form'
        return action_vals
