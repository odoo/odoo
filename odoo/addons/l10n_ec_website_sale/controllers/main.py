# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class L10nECWebsiteSale(WebsiteSale):

    def _get_mandatory_fields_billing(self, country_id=False):
        """Extend mandatory fields to add new identification and responsibility fields when company is Ecuador"""
        res = super()._get_mandatory_fields_billing(country_id)
        if request.website.sudo().company_id.country_id.code == "EC":
            res += ["l10n_latam_identification_type_id", "vat"]
        return res

    def _get_country_related_render_values(self, kw, render_values):
        res = super()._get_country_related_render_values(kw, render_values)
        if request.website.sudo().company_id.country_id.code == "EC":
            res.update({
                'identification': kw.get('l10n_latam_identification_type_id'),
                'identification_types': request.env['l10n_latam.identification.type'].search(
                    ['|', ('country_id', '=', False), ('country_id.code', '=', 'EC')]),
            })
        return res

    def _get_vat_validation_fields(self, data):
        res = super()._get_vat_validation_fields(data)
        latam_id_type_data = data.get("l10n_latam_identification_type_id")
        if request.website.sudo().company_id.country_id.code == "EC":
            res.update({
                'l10n_latam_identification_type_id': int(latam_id_type_data) if latam_id_type_data else False,
                'name': data.get('name', False),
            })
        return res

    def _get_shop_payment_values(self, order, **kwargs):
        payment_values = super()._get_shop_payment_values(order, **kwargs)
        company = order.company_id
        # Do not show payment methods without l10n_ec_sri_payment_id.
        # Payment methods without this fields could cause issues since we require a l10n_ec_sri_payment_id to post a move.
        if company.account_fiscal_country_id.code == 'EC':
            payment_methods = payment_values['payment_methods_sudo'].filtered(lambda pm: bool(pm.l10n_ec_sri_payment_id))
            payment_values['payment_methods_sudo'] = payment_methods
        return payment_values
