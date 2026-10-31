# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


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

    @api.model
    def _get_portal_additional_identifiers(self, country_sudo, **kwargs):
        optional, mandatory = super()._get_portal_additional_identifiers(country_sudo, **kwargs)
        order_sudo = kwargs.get('order_sudo')
        if order_sudo and order_sudo.company_id.account_fiscal_country_id.code == 'AR' and country_sudo.code == 'AR':
            company = order_sudo.company_id
            amount = order_sudo.currency_id._convert(
                order_sudo.amount_total, company.currency_id, company, order_sudo.date_order,
            )
            limit = company.l10n_ar_final_consumer_limit
            if company.currency_id.compare_amounts(amount, limit) > 0:
                mandatory.add('AR_DNI')
        return optional, mandatory
