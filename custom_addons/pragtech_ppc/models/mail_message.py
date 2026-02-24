# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MailMessage(models.Model):
    _name = 'mail.messages'

    @api.model
    def _get_default_author(self):
        return self.env.user.partner_id

    date = fields.Datetime('Date', default=fields.Datetime.now)
    from_stage = fields.Many2one('stage.master', 'From Stage')
    to_stage = fields.Many2one('stage.master', 'Stage')
    remark = fields.Char('Remark')
    author_id = fields.Many2one('res.partner', 'UserName', index=1, ondelete='set null', default=_get_default_author,
                                help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    is_use = fields.Boolean('Is Use')
    res_id = fields.Integer('Related Document ID', index=1)
    model = fields.Char('Related Document Model', index=1)

