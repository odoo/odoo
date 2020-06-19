# -*- coding: utf-8 -*-

from odoo import api, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def generate_email(self, res_ids, fields):
        res = super().generate_email(res_ids, fields)

        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False

        if self.model != 'account.move':
            return res

        existing_attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', 'in', res_ids),
                ('edi_format_id', '!=', False)])

        for record in self.env[self.model].browse(res_ids):
            available_formats = existing_attachments.filtered(lambda a: a.res_id == record.id)
            missing_formats = record.journal_id.edi_format_ids.filtered(lambda f: f._origin.id not in available_formats.edi_format_id.ids)
            new_attachments = missing_formats._create_ir_attachments(record)
            available_formats |= new_attachments
            (res[record.id] if multi_mode else res).setdefault('attachments', []).extend([(a.name, a.datas) for a in available_formats])

        return res
