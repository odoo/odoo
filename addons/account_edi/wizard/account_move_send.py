# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    def _get_mail_attachment_from_doc(self, doc):
        attachment_sudo = doc.sudo().attachment_id
        if attachment_sudo.res_model and attachment_sudo.res_id:
            return [{
                'id': attachment_sudo.id,
                'name': attachment_sudo.name,
                'mimetype': attachment_sudo.mimetype,
                'placeholder': False,
            }]
        return []

    def _get_default_email_attachment_data(self, mail_template, move):
        """ Returns all the placeholder data and mail template data
        """
        results = super()._get_default_email_attachment_data(mail_template, move)
        for doc in move.edi_document_ids:
            results += self._get_mail_attachment_from_doc(doc)
        return results
