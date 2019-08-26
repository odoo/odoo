from odoo import models


class ThemeBootswatch(models.AbstractModel):
    _inherit = 'theme.utils'

    def _theme_a_post_copy(self, mod):
        self.disable_view('website_theme_install.customize_modal')
