# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class Users(models.Model):
    """ Update of res.users class
        - add a preference about username for livechat purpose
    """
    _inherit = 'res.users'

    livechat_username = fields.Char("Livechat Username", help="This username will be used as your name in the livechat channels.")

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on livechat_username
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(Users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(['livechat_username'])
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        type(self).SELF_READABLE_FIELDS.extend(['livechat_username'])
        return init_res
