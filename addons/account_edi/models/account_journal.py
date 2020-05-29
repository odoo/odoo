# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    edi_format_ids = fields.Many2many(comodel_name='account.edi.format',
                                      string='Electronic invoicing',
                                      help='Send XML/EDI invoices',
                                      domain="[('hide_on_journal', '=', 'import_export')]")

    def _create_invoice_from_single_attachment(self, attachment):
        invoice = self.env['account.edi.format'].search([])._create_invoice_from_attachment(attachment)
        if invoice:
            # with_context: we don't want to import the attachment since the invoice was just created from it.
            invoice.with_context(no_new_invoice=True).message_post(attachment_ids=[attachment.id])
            return invoice
        return super()._create_invoice_from_single_attachment(attachment)
