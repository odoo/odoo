# -*- coding: utf-8 -*-
from odoo import fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    path = fields.Char(string="Discussion Path", index=True, help='Used to display messages in a paragraph-based chatter using a unique path;')
