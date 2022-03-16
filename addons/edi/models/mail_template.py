# -*- coding: utf-8 -*-

from odoo import models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def _get_edi_attachments(self, flows):
        """ Return the information about the attachments of the edi flows for adding them in the mail.

        :param flows: a recordset of EDI flows
        :return: list with a tuple with the name and base64 content of the attachment
        """
        if not flows.edi_file_ids.attachment_id:
            return []
        return [(attachment.name, attachment.datas) for attachment in flows.edi_file_ids.attachment_id]

    def generate_email(self, res_ids, fields):
        res = super().generate_email(res_ids, fields)

        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False

        if 'edi_flow_ids' not in self.env[self.model]._fields:  # todo can also check if self inherit from the mixin
            return res

        records = self.env[self.model].browse(res_ids)
        for record in records:
            flows = record.edi_flow_ids.filtered(lambda f: (
                f.flow_type == 'send'
                and f._get_edi_format_settings().get('attachments_required_in_mail')
            ))
            record_data = (res[record.id] if multi_mode else res)
            record_data.setdefault('attachments', [])
            record_data['attachments'] += self._get_edi_attachments(flows)

        return res
