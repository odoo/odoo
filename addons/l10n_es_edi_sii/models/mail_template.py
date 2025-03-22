from odoo import models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def _get_edi_attachments(self, document):
        # When an invoice is signed, an electronic document is created (i.e. jsondump.json)
        # Prevent this document to be added in "SEND & PRINT" wizard
        if document.name == 'jsondump.json' and document.edi_format_id.code == 'es_sii':
            return {}
        return super()._get_edi_attachments(document)
