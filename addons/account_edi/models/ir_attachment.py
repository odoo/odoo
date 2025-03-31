# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_government_document(self):
        # sudo: account.edi.document - constraint that must be applied regardless of ACL
        linked_edi_documents = self.env['account.edi.document'].sudo().search([('attachment_id', 'in', self.ids)])
        linked_edi_formats_ws = linked_edi_documents.edi_format_id.filtered(lambda edi_format: edi_format._needs_web_services())
        if linked_edi_formats_ws:
            raise UserError(_("You can't unlink an attachment being an EDI document sent to the government."))
