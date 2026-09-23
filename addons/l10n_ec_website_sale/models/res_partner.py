# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_mandatory_additional_identifiers(self, country_sudo, **kwargs):
        identifiers = super()._get_mandatory_additional_identifiers(country_sudo, **kwargs)
        order_sudo = kwargs.get('order_sudo')
        if order_sudo and order_sudo.company_id.country_code == 'EC' and country_sudo.code == 'EC':
            company = order_sudo.company_id
            amount = order_sudo.currency_id._convert(
                order_sudo.amount_total, company.currency_id, company, order_sudo.date_order,
            )
            limit = order_sudo.website_id.l10n_ec_final_consumer_limit
            if company.currency_id.compare_amounts(amount, limit) > 0:
                identifiers.add('EC_DNI')
        return identifiers
