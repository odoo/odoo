# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ThemeUtils(models.AbstractModel):
    _name = 'theme.utils'
    _inherit = 'theme.utils'

    category_style_templates = [
        'website_sale.filmstrip_categories_bordered',
        'website_sale.filmstrip_categories_tabs',
        'website_sale.filmstrip_categories_pills',
        'website_sale.filmstrip_categories_images',
        'website_sale.filmstrip_categories_grid',
        'website_sale.filmstrip_categories_large_images',
    ]

    def enable_view(self, xml_id):
        """Override of `theme.utils` to disable all category style templates when enabling one."""
        if xml_id in self.category_style_templates:
            for template in self.category_style_templates:
                self.disable_view(template)
        super().enable_view(xml_id)
