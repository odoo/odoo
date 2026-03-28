from odoo import models


class ThemeUtils(models.AbstractModel):
    _inherit = 'theme.utils'

    def _theme_odoo_experts_post_copy(self, mod):
        self.enable_view('website.template_footer_contact')
