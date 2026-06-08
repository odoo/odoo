from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Website Dependent Settings
    l10n_ar_website_sale_show_both_prices = fields.Boolean(
        related='website_id.l10n_ar_website_sale_show_both_prices',
        readonly=False,
    )
