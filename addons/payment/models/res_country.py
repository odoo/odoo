# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

# Import the payment provider modules with aliases to avoid circular import errors.
import odoo.addons.payment_mercado_pago as mercado_pago
import odoo.addons.payment_stripe as stripe


class ResCountry(models.Model):
    _inherit = 'res.country'

    is_mercado_pago_supported_country = fields.Boolean(compute='_compute_provider_support')
    is_stripe_supported_country = fields.Boolean(compute='_compute_provider_support')

    @api.depends('code')
    def _compute_provider_support(self):
        for country in self:
            country.is_stripe_supported_country = stripe.const.COUNTRY_MAPPING.get(
                country.code, country.code
            ) in stripe.const.SUPPORTED_COUNTRIES
            country.is_mercado_pago_supported_country = (
                country.code in mercado_pago.const.SUPPORTED_COUNTRIES
            )
