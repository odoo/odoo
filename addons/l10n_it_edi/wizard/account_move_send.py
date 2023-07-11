# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    def _get_mail_attachment_from_doc(self, doc):
        if doc.edi_format_id.code == 'fattura_pa':
            return self.env['ir.attachment']
        return super()._get_mail_attachment_from_doc(doc)
