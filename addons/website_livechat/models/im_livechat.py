# -*- coding: utf-8 -*-
from openerp import api, models, fields
from openerp.addons.website.models.website import slug


class im_livechat_channel(models.Model):
    _name = 'im_livechat.channel'
    _inherit = ['im_livechat.channel', 'website.published.mixin']

    @api.multi
    def _website_url(self):
        super(im_livechat_channel, self)._website_url()
        for channel in self:
            channel.website_url = "/livechat/channel/%s" % (slug(channel),)

    website_description = fields.Html("Website description", default=False, help="Description of the channel displayed on the website page")
