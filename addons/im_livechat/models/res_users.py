# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    def __init__(self, pool, cr):
        """ Override of __init__ to allow set simultaneous chat limit"""
        init_res = super(ResUsers, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(['enable_chat_limit', 'chat_limit'])
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        type(self).SELF_READABLE_FIELDS.extend(['enable_chat_limit', 'chat_limit'])
        return init_res

    enable_chat_limit = fields.Boolean(string="Livechat Limit", groups="im_livechat.im_livechat_group_user")
    chat_limit = fields.Integer(string="Maximum Simultaneous Chat(s)", groups="im_livechat.im_livechat_group_user")
