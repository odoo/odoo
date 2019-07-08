# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class LivechatRequest(models.Model):
    _name = 'im_livechat.request'
    _description = 'Chat request sent by an operator to a website visitor'

    visitor_id = fields.Many2one('website.visitor', string='Visitor')
    mail_channel_id = fields.Many2one('mail.channel', string='Operator', help="""Operator that requested the chat""")

    _sql_constraints = [
        ('visitor_id_uniq', 'unique (visitor_id)', "Only one chat request per visitor !"),
        ('mail_channel_id_uniq', 'unique (mail_channel_id)', "Only one chat request per mail channel !"),
    ]
