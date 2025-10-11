# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    enabled_gmc_src = fields.Boolean(
        default=lambda self: self.env['res.groups']._is_feature_enabled(
            'website_sale_product_feed.group_product_feed',
        ),
    )

    def _populate_product_feeds(self):
        """Populate product feeds for the website with default values."""
        for website in self:
            website.env['product.feed'].create({
                'name': website.env._("GMC 1"),
                'website_id': website.id,
            })
