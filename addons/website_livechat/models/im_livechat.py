# -*- coding: utf-8 -*-
from odoo.addons import website, im_livechat
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.tools.translate import html_translate


class ImLivechatChannel(models.Model, im_livechat.ImLivechatChannel, website.WebsitePublishedMixin):

    _name = 'im_livechat.channel'

    def _compute_website_url(self):
        super(ImLivechatChannel, self)._compute_website_url()
        for channel in self:
            channel.website_url = "/livechat/channel/%s" % (self.env['ir.http']._slug(channel),)

    website_description = fields.Html(
        "Website description", default=False, translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False, sanitize_form=False,
        help="Description of the channel displayed on the website page")
