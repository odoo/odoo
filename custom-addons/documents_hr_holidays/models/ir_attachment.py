# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _create_document(self, vals):
        leave_attachments = self.filtered(lambda a: a.res_model == 'hr.leave' and not a.res_id)
        if vals.get('res_id') and leave_attachments:
            leave = self.env['hr.leave'].browse(vals['res_id'])
            doc_vals = [
                leave._get_document_vals(attachment)
                for attachment in leave_attachments
            ]
            doc_vals = [vals for vals in doc_vals if vals]
            self.env['documents.document'].create(doc_vals)

        return super(IrAttachment, (self - leave_attachments))._create_document(vals)
