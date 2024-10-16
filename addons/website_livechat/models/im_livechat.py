# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.tools.translate import html_translate
from odoo.addons import im_livechat, website


class Im_LivechatChannel(im_livechat.Im_LivechatChannel, website.WebsitePublishedMixin):


    def _compute_website_url(self):
        super()._compute_website_url()
        for channel in self:
            channel.website_url = "/livechat/channel/%s" % (self.env['ir.http']._slug(channel),)

    website_description = fields.Html(
        "Website description", default=False, translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False, sanitize_form=False,
        help="Description of the channel displayed on the website page")
