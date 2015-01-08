# -*- coding: utf-8 -*-
from openerp import models, fields


class im_livechat_channel(models.Model):

    _inherit = 'im_livechat.channel'

    website_published = fields.Boolean("Website published", default=False, help="If checked, the channel and its ratings will be display on your website")
    website_description = fields.Html("Website description", default=False, help="Description of the channel displayed on the website page")
