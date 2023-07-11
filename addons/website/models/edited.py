# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Edited(models.AbstractModel):
    _inherit = 'web_editor.edited'

    @api.model
    def _get_base_edited_html_fields(self):
        result = super()._get_base_edited_html_fields()
        result.extend([
            ('website', 'custom_code_head', []),
            ('website', 'custom_code_footer', []),
            ('website', 'robots_txt', []),
            ('website.menu', 'mega_menu_content', []),
            ('theme.website.menu', 'mega_menu_content', []),
        ])
        return result
