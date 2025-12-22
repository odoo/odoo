from odoo import models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_mail_attachment_from_doc(self, doc):
        if doc.name == 'jsondump.json' and doc.edi_format_id.code == 'es_sii':
            return self.env['ir.attachment']
        return super()._get_mail_attachment_from_doc(doc)
