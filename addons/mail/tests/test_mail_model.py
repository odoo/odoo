# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailTest(models.Model):
    """ A mail.channel is a discussion group that may behave like a listener
    on documents. """
    _description = 'Test Mail Model'
    _name = 'mail.test'
    _mail_post_access = 'read'
    _inherit = ['mail.thread']

    name = fields.Char()
    alias_id = fields.Many2one(
        'mail.alias', 'Alias')
