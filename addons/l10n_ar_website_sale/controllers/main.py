# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.tools import str2bool

from odoo.addons.website_sale.controllers.main import WebsiteSale


class L10nArWebsiteSale(WebsiteSale):

    def _create_or_update_address(
        self, partner_sudo, address_type='billing', use_delivery_as_billing=False, **form_data,
    ):
        partner_sudo, feedback_dict = super()._create_or_update_address(
            partner_sudo,
            address_type=address_type,
            use_delivery_as_billing=use_delivery_as_billing,
            **form_data,
        )
        commercial_partner_sudo = partner_sudo.commercial_partner_id
        if (
            form_data.get('order_sudo')
            and not feedback_dict.get('invalid_fields')
            and request.env.company.country_code == 'AR'
            and (address_type == 'billing' or str2bool(use_delivery_as_billing or 'false'))
            and not commercial_partner_sudo.l10n_ar_afip_responsibility_type_id
        ):
            commercial_partner_sudo.l10n_ar_afip_responsibility_type_id = request.env.ref(
                'l10n_ar.res_CF' if partner_sudo.country_id.code == 'AR' else 'l10n_ar.res_EXT',
            )
        return partner_sudo, feedback_dict
