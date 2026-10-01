# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_tbai_document_xml(self):
        # sudo: l10n_es_edi_tbai.document - constraint that must be applied regardless of ACL
        linked_documents = self.env['l10n_es_edi_tbai.document'].sudo().search([('xml_attachment_id', 'in', self.ids)])
        if linked_documents:
            raise UserError(_("You can't unlink an attachment being a TicketBAI document sent to the government."))
