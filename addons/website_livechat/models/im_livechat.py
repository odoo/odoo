# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.http_routing.models.ir_http import slug
from odoo.tools.translate import html_translate


class ImLivechatChannel(models.Model):

    _name = 'im_livechat.channel'
    _inherit = ['im_livechat.channel', 'website.published.mixin']

    def _compute_website_url(self):
        super()._compute_website_url()
        for channel in self.filtered(lambda record: record.id):
            channel.website_url = f"/livechat/channel/{slug(channel)}"

    website_description = fields.Html(
        "Website description", default=False, translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False, sanitize_form=False,
        help="Description of the channel displayed on the website page")
