# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Website(models.Model):
    _inherit = 'website'

    def _populate_product_feeds(self):
        """Populate product feeds for the website with default values."""
        for website in self:
            website.env['product.feed'].create({
                'name': website.env._("GMC 1"),
                'website_id': website.id,
                'lang_id': website.default_lang_id.id,
            })
