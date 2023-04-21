# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    def _get_default_mail_attachments_data(self, mail_template, move):
        """ Returns all the placeholder data and mail template data
        """
        results = super()._get_default_mail_attachments_data(mail_template, move)

        for doc in move.edi_document_ids:
            attachment_sudo = doc.sudo().attachment_id
            if attachment_sudo.res_model and attachment_sudo.res_id:
                results.append({
                    'id': attachment_sudo.id,
                    'name': attachment_sudo.name,
                    'mimetype': attachment_sudo.mimetype,
                    'placeholder': False,
                })
        return results
