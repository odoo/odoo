from odoo import models


class ThemeUtils(models.AbstractModel):
    _inherit = 'theme.utils'

    def _theme_common_post_copy(self, mod):
        # Reset all default color when switching themes
        self.disable_asset('theme_common.option_colors_02_variables')
        self.disable_asset('theme_common.option_colors_03_variables')
        self.disable_asset('theme_common.option_colors_04_variables')
        self.disable_asset('theme_common.option_colors_05_variables')
        self.disable_asset('theme_common.option_colors_06_variables')
        self.disable_asset('theme_common.option_colors_07_variables')
        self.disable_asset('theme_common.option_colors_08_variables')
