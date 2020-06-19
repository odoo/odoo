# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    edi_document_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'account.move'), ('edi_format_id', '!=', False)])

    def post(self):
        # OVERRIDE
        # Generate the electronic documents for the move.
        existing_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', 'in', self.ids),
            ('edi_format_id', 'in', self.journal_id.edi_format_ids.ids)])
        existing_attachments.unlink()
        res = super(AccountMove, self).post()
        for move in self:
            move.journal_id.edi_format_ids._create_ir_attachments(move)

        return res

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        # OVERRIDE
        # When posting a message, analyse the attachment to check if it is an EDI document and update the invoice
        # with the data.
        res = super(AccountMove, self).message_post(**kwargs)

        if len(self) != 1 or self.env.context.get('no_new_invoice') or not self.is_invoice(include_receipts=True):
            return res

        attachments = self.env['ir.attachment'].browse(kwargs.get('attachment_ids', []))
        odoobot = self.env.ref('base.partner_root')
        if attachments and self.state != 'draft':
            self.message_post(body='The invoice is not a draft, it was not updated from the attachment.',
                              message_type='comment',
                              subtype_xmlid='mail.mt_note',
                              author_id=odoobot.id)
            return res
        if attachments and self.line_ids:
            self.message_post(body='The invoice already contains lines, it was not updated from the attachment.',
                              message_type='comment',
                              subtype_xmlid='mail.mt_note',
                              author_id=odoobot.id)
            return res

        for attachment in attachments:
            invoice = self.env['account.edi.format'].search([])._update_invoice_from_attachment(attachment, self)
            break

        return res
