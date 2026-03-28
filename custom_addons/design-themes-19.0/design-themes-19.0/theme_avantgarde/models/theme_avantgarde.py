from odoo import models


class ThemeUtils(models.AbstractModel):
    _inherit = 'theme.utils'

    def _theme_avantgarde_post_copy(self, mod):
        self.enable_view('website.template_header_hamburger')
        self.enable_view('website.template_header_hamburger_align_right')
        self.enable_view('website.no_autohide_menu')

        self.enable_view('website.template_footer_descriptive')

