from odoo import models
from odoo.addons import account_edi


class AccountMoveSend(account_edi.AccountMoveSend):

    def _get_mail_attachment_from_doc(self, doc):
        if doc.name == 'jsondump.json' and doc.edi_format_id.code == 'es_sii':
            return self.env['ir.attachment']
        return super()._get_mail_attachment_from_doc(doc)
