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

        groupby_moves = {}
        all_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', 'in', res_ids),
            ('edi_format_id', '!=', False)
        ])
        for attachment in all_attachments:
            groupby_moves.setdefault(attachment.res_id, self.env['ir.attachment'])
            groupby_moves[attachment.res_id] |= attachment

        for move_id, attachments in groupby_moves.items():
            record_data = (res[move_id] if multi_mode else res)
            record_data.setdefault('attachments', [])
            record_data['attachments'] += [(attachment.name, attachment.datas) for attachment in attachments]

        return res
