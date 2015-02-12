# -*- coding: utf-8 -*-
from openerp import models, fields


class im_livechat_channel(models.Model):
    _name = 'im_livechat.channel'
    _inherit = ['im_livechat.channel', 'website.published.mixin']

    website_description = fields.Html("Website description", default=False, help="Description of the channel displayed on the website page")
