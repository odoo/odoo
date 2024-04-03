# -*- coding: utf-8 -*-

from odoo import models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def _get_edi_attachments(self, document):
        # EXTENDS account_edi
        # Avoid having factur-x.xml in the 'send & print' wizard
        if document.edi_format_id.code == 'facturx_1_0_05':
            return {}
        return super()._get_edi_attachments(document)
