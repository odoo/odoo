from odoo import models


class ThemeUtils(models.AbstractModel):
    _inherit = 'theme.utils'

    def _theme_cobalt_post_copy(self, mod):
        self.enable_asset("website.ripple_effect_scss")
        self.enable_asset("website.ripple_effect_js")
        self.enable_view("website.template_header_boxed")
        self.enable_view("website.template_footer_call_to_action")
        self.enable_view("website.header_navbar_pills_style")
