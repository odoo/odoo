# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.Model):
    _inherit = 'res.config.settings'

    group_gmc_feed = fields.Boolean(
        string="Google Merchant Center Data Source",
        implied_group='website_sale_gmc.group_product_feed',
        group='base.group_user',
        related='website_id.enabled_gmc_src',
        readonly=False,
    )

    _check_gmc_ecommerce_access = models.Constraint('CHECK (TRUE)', "Disable the constraint")

    def set_values(self):
        """Override to pre-populate the website feeds if none already exists."""
        super().set_values()

        if self.group_gmc_feed and not self.env['product.feed'].search_count(
            [('website_id', '=', self.website_id.id)], limit=1
        ):
            self.website_id._populate_product_feeds()

    @api.readonly
    def action_open_product_feeds(self):
        """Open the list view to manage the feed specific to the current website."""
        self.ensure_one()
        return {
            'name': self.env._("Product Feeds"),
            'type': 'ir.actions.act_window',
            'res_model': 'product.feed',
            'views': [(False, 'list')],
            'target': 'new',
            'context': {
                'default_website_id': self.website_id.id,
                'default_lang_id': self.website_id.default_lang_id.id,
                'hide_website_column': True,
            },
            'domain': [('website_id', '=', self.website_id.id)],
        }
