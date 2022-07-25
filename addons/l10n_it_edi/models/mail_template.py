# -*- coding: utf-8 -*-

from odoo import models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def _get_edi_attachments(self, document):
        """
        Will return the information about the attachment of the edi document for adding the attachment in the mail.
        Can be overridden where e.g. a zip-file needs to be sent with the individual files instead of the entire zip
        :param document: an edi document
        :return: list with a tuple with the name and base64 content of the attachment
        """
        if document.edi_format_id.code == 'fattura_pa':
            return {}
        return super()._get_edi_attachments(document)
