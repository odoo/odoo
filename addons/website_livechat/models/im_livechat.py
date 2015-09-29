# -*- coding: utf-8 -*-
from openerp import api, models, fields
from openerp.addons.website.models.website import slug


class ImLivechatChannel(models.Model):

    _name = 'im_livechat.channel'
    _inherit = ['im_livechat.channel', 'website.published.mixin']

    @api.v7
    # TODO : when mixin in new api.v8, change this !
    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = super(ImLivechatChannel, self)._website_url(cr, uid, ids, field_name, arg, context=context)
        for channel in self.browse(cr, uid, ids, context=context):
            res[channel.id] = "/livechat/channel/%s" % (slug(channel),)
        return res

    website_description = fields.Html("Website description", default=False, help="Description of the channel displayed on the website page")
