# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from .im_livechat_channel import THEME_COLOR_SOURCES

THEME_COLOR_KEYS = {"color-palettes-name", *(name for sources in THEME_COLOR_SOURCES.values() for name in sources)}
THEME_PALETTE_URL = "/website/static/src/scss/options/colors/user_color_palette.scss"


class WebsiteAssets(models.AbstractModel):
    _inherit = "website.assets"

    @api.model
    def make_scss_customization(self, url, values):
        if THEME_COLOR_KEYS & values.keys():
            self._schedule_livechat_theme_colors_sync()
        return super().make_scss_customization(url, values)

    @api.model
    def reset_asset(self, url, bundle):
        if url == THEME_PALETTE_URL:
            self._schedule_livechat_theme_colors_sync()
        return super().reset_asset(url, bundle)

    @api.model
    def save_asset(self, url, bundle, content, file_type):
        if url == THEME_PALETTE_URL:
            self._schedule_livechat_theme_colors_sync()
        return super().save_asset(url, bundle, content, file_type)

    @api.model
    def _schedule_livechat_theme_colors_sync(self):
        website = self.env.website or self.env["website"].browse(self.env.context.get("host_id"))
        website.sudo()._schedule_livechat_theme_colors_sync()
