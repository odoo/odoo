# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def unlink(self):
        # OVERRIDE
        linked_edi_documents = self.env['account.edi.document'].search([('attachment_id', 'in', self.ids)])
        linked_edi_formats_ws = linked_edi_documents.edi_format_id.filtered(lambda edi_format: edi_format._needs_web_services())
        if linked_edi_formats_ws:
            raise UserError(_("You can't unlink an attachment being an EDI document sent to the government."))
        return super().unlink()
