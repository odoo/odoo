from odoo import models


class ThemeUtils(models.AbstractModel):
    _inherit = 'theme.utils'

    def _theme_bistro_post_copy(self, mod):
        self.enable_view('website.template_header_vertical')
        self.enable_view('website.header_navbar_pills_style')

        self.enable_asset("website.ripple_effect_scss")
        self.enable_asset("website.ripple_effect_js")
