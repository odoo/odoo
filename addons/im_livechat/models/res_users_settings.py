# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import mail


class ResUsersSettings(mail.ResUsersSettings):

    livechat_username = fields.Char("Livechat Username", help="This username will be used as your name in the livechat channels.")
    livechat_lang_ids = fields.Many2many(comodel_name='res.lang', string='Livechat languages',
                            help="These languages, in addition to your main language, will be used to assign you to Live Chat sessions.")
