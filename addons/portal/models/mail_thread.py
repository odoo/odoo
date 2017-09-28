# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    _mail_post_token_field = 'access_token' # token field for external posts, to be overridden

    website_message_ids = fields.One2many('mail.message', 'res_id', string='Website Messages',
        domain=lambda self: [('model', '=', self._name), ('message_type', '=', 'comment')], auto_join=True,
        help="Website communication history")
