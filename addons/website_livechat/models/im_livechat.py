# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.addons.website.models.website import slug


class ImLivechatChannel(models.Model):

    _name = 'im_livechat.channel'
    _inherit = ['im_livechat.channel', 'website.published.mixin']

    @api.multi
    def _website_url(self, name, arg):
        res = super(ImLivechatChannel, self)._website_url(name, arg)
        for channel in self:
            res[channel.id] = "/livechat/channel/%s" % (slug(channel),)
        return res

    website_description = fields.Html("Website description", help="Description of the channel displayed on the website page")
