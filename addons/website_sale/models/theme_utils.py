from odoo import models


class ThemeUtils(models.AbstractModel):
    _inherit = 'theme.utils'

    @property
    def _footer_templates(self):
        return ['website_sale.template_footer_website_sale'] + super()._footer_templates
