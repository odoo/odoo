# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    path = fields.Char(
        'Discussion Path', index=True,
        help='Used to display messages in a paragraph-based chatter using a unique path;')
