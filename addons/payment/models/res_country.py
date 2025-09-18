# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCountry(models.Model):
    _inherit = 'res.country'

    is_mercado_pago_supported_country = fields.Boolean(compute='_compute_provider_support')
    is_stripe_supported_country = fields.Boolean(compute='_compute_provider_support')

    @api.depends('code')
    def _compute_provider_support(self):
        # Lazy-import provider constants only when the module is actually installed.
        # Avoids importing uninstalled addons at startup (they are on disk but not loaded).
        init_modules = self.env.registry._init_modules
        mp_countries = set()
        stripe_countries = set()
        stripe_mapping = {}
        if 'payment_mercado_pago' in init_modules:
            from odoo.addons.payment_mercado_pago import const as mp_const
            mp_countries = mp_const.SUPPORTED_COUNTRIES
        if 'payment_stripe' in init_modules:
            from odoo.addons.payment_stripe import const as stripe_const
            stripe_countries = stripe_const.SUPPORTED_COUNTRIES
            stripe_mapping = stripe_const.COUNTRY_MAPPING
        for country in self:
            country.is_stripe_supported_country = (
                stripe_mapping.get(country.code, country.code) in stripe_countries
            )
            country.is_mercado_pago_supported_country = country.code in mp_countries
