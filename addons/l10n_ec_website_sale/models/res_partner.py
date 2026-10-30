# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_portal_additional_identifiers(self, country_sudo, **kwargs):
        optional, mandatory = super()._get_portal_additional_identifiers(country_sudo, **kwargs)
        order_sudo = kwargs.get('order_sudo')
        if order_sudo and order_sudo.company_id.account_fiscal_country_id.code == 'EC' and country_sudo.code == 'EC':
            company = order_sudo.company_id
            amount = order_sudo.currency_id._convert(
                order_sudo.amount_total, company.currency_id, company, order_sudo.date_order,
            )
            limit = company.l10n_ec_final_consumer_limit
            if company.currency_id.compare_amounts(amount, limit) > 0:
                mandatory.add('EC_DNI')
        return optional, mandatory
