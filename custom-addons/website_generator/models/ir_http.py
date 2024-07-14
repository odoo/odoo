# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super().session_info()
        last_generator_request = self.env["website_generator.request"].sudo().search([], order="id desc", limit=1)
        if last_generator_request:
            result["show_scraper_systray"] = not last_generator_request.notified
        return result
