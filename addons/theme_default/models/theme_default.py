from odoo import models

class ThemeDefault(models.AbstractModel):
    _inherit = 'theme.utils'

    def _theme_default_post_copy(self, mod):
        self.env.ref('website_theme_install.customize_modal').write({'active': False});
