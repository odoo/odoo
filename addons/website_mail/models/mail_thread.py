# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


# TODO for trunk, remove me
class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    website_message_ids = fields.One2many('mail.message', 'res_id',
        domain=lambda self: ['&', ('model', '=', self._name), ('message_type', '=', 'comment')],
        string='Website Messages', help="Website communication history")
