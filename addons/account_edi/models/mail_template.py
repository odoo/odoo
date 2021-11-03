# -*- coding: utf-8 -*-

from odoo import models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def _get_edi_attachments(self, document):
        """
        Will either return the information about the attachment of the edi document for adding the attachment in the
        mail, or the attachment id to be linked to the 'send & print' wizard.
        Can be overridden where e.g. a zip-file needs to be sent with the individual files instead of the entire zip
        IMPORTANT:
        * If the attachment's id is returned, no new attachment will be created, the existing one on the move is linked
        to the wizard (see _onchange_template_id in mail.compose.message).
        * If the attachment's content is returned, a new one is created and linked to the wizard. Thus, when sending
        the mail (clicking on 'send & print' in the wizard), a new attachment is added to the move (see
        _action_send_mail in mail.compose.message).
        :param document: an edi document
        :return: dict:
            {'attachments': tuple with the name and base64 content of the attachment}
            OR
            {'attachment_ids': list containing the id of the attachment}
        """
        if not document.attachment_id:
            return {}
        return {'attachment_ids': [document.attachment_id.id]}

    def _generate_template_attachments(self, res_ids, render_fields, render_results=None):
        render_res = super()._generate_template_attachments(res_ids, render_fields, render_results=render_results)

        if self.model not in ['account.move', 'account.payment']:
            return render_res
        if not 'attachments' in render_fields:
            return render_res

        records = self.env[self.model].browse(res_ids)
        for record in records:
            for doc in record.edi_document_ids:
                render_res[record.id].setdefault('attachment_ids', [])
                render_res[record.id].setdefault('attachments', [])
                attachments = self._get_edi_attachments(doc)
                render_res[record.id]['attachment_ids'] += attachments.get('attachment_ids', [])
                render_res[record.id]['attachments'] += attachments.get('attachments', [])

        return render_res
