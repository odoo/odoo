# -*- coding: utf-8 -*-

from openerp import api, fields, models


class MessageReference(models.Model):
    _name = 'mail.message.reference'

    res_id = fields.Integer('Related Document ID')
    model = fields.Char('Related Document Model')
    mail_message_id = fields.Many2one('mail.message')
    record_name = fields.Char('Record Name', compute='_get_record_name', store=True)

    @api.depends('model', 'res_id')
    def _get_record_name(self):
        for record in self:
            record.record_name = self.env[record.model].browse(record.res_id).display_name
