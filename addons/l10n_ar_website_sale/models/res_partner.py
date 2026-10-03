# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_mandatory_billing_address_fields(self, country_sudo, **kwargs):
        field_names = super()._get_mandatory_billing_address_fields(country_sudo, **kwargs)
        order_sudo = kwargs.get('order_sudo')
        website_sudo = order_sudo and order_sudo.website_id
        if website_sudo and not website_sudo.with_context(website_id=website_sudo.id).is_view_active(
            'website_sale.address_b2b',
        ):
            # The ARCA Responsibility select sits in the B2B block, hidden with it.
            field_names.discard('l10n_ar_afip_responsibility_type_id')
        return field_names

    def _get_mandatory_additional_identifiers(self, country_sudo, **kwargs):
        identifiers = super()._get_mandatory_additional_identifiers(country_sudo, **kwargs)
        order_sudo = kwargs.get('order_sudo')
        if order_sudo and order_sudo.company_id.country_code == 'AR' and country_sudo.code == 'AR':
            company = order_sudo.company_id
            amount = order_sudo.currency_id._convert(
                order_sudo.amount_total, company.currency_id, company, order_sudo.date_order,
            )
            limit = order_sudo.website_id.l10n_ar_final_consumer_limit
            if company.currency_id.compare_amounts(amount, limit) > 0:
                identifiers.add('AR_DNI')
        return identifiers
