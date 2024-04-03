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
        attachment_sudo = document.sudo().attachment_id
        if not attachment_sudo:
            return {}
        if not (attachment_sudo.res_model and attachment_sudo.res_id):
            # do not return system attachment not linked to a record
            return {}
        if len(self._context.get('active_ids', [])) > 1:
            # In mass mail mode 'attachments_ids' is removed from template values
            # as they should not be rendered
            return {'attachments': [(attachment_sudo.name, attachment_sudo.datas)]}
        return {'attachment_ids': [attachment_sudo.id]}

    def generate_email(self, res_ids, fields):
        res = super().generate_email(res_ids, fields)

        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False

        if self.model not in ['account.move', 'account.payment']:
            return res

        records = self.env[self.model].browse(res_ids)
        for record in records:
            record_data = (res[record.id] if multi_mode else res)
            for doc in record.edi_document_ids:
                record_data.setdefault('attachments', [])
                attachments = self._get_edi_attachments(doc)
                record_data['attachment_ids'] += attachments.get('attachment_ids', [])
                record_data['attachments'] += attachments.get('attachments', [])

        return res
