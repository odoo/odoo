# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _theme_load(self, website):
        super()._theme_load(website)
        # The new theme brings its own palette, without customizing the colors.
        website.sudo()._schedule_livechat_theme_colors_sync()
