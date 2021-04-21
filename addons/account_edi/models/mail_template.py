# -*- coding: utf-8 -*-

from odoo import api, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def _get_edi_attachments(self, attachment_id, record_data):
        if not attachment_id:
            return record_data
        record_data.setdefault('attachments', [])
        record_data['attachments'].append((attachment_id.name, attachment_id.datas))
        return record_data

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

                # The EDI format will be embedded directly inside the PDF and then, don't need to be added to the
                # wizard.
                if doc.edi_format_id._is_embedding_to_invoice_pdf_needed():
                    continue
                record_data = self._get_edi_attachments(doc, record_data)

        return res
