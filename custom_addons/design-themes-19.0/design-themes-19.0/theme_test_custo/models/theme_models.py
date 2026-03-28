# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ThemeUtils(models.AbstractModel):
    _inherit = 'theme.utils'

    @property
    def _header_templates(self):
        return ['theme_test_custo.template_header_custom'] + super()._header_templates

    @property
    def _footer_templates(self):
        return ['theme_test_custo.template_footer_custom'] + super()._footer_templates

    def _theme_test_custo_post_copy(self, mod):
        self.enable_view('theme_test_custo.template_header_custom')
        self.enable_view('theme_test_custo.template_footer_custom')
