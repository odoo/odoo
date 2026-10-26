# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from .im_livechat_channel import THEME_COLOR_SOURCES

THEME_COLOR_KEYS = {"color-palettes-name", *(name for sources in THEME_COLOR_SOURCES.values() for name in sources)}


class WebsiteAssets(models.AbstractModel):
    _inherit = "website.assets"

    @api.model
    def make_scss_customization(self, url, values):
        if THEME_COLOR_KEYS & values.keys():
            website = self.env.website or self.env["website"].browse(self.env.context.get("host_id"))
            website.sudo()._schedule_livechat_theme_colors_sync()
        return super().make_scss_customization(url, values)
