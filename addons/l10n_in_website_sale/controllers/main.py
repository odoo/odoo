from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSaleInherit(WebsiteSale):

    def _validate_address_values(
        self,
        address_values,
        partner_sudo,
        address_type,
        use_delivery_as_billing,
        required_fields,
        is_main_address,
        **_kwargs,
    ):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values,
            partner_sudo,
            address_type,
            use_delivery_as_billing,
            required_fields,
            is_main_address,
            **_kwargs,
        )
        if not (country_id := address_values.get('country_id')):
            return invalid_fields, missing_fields, error_messages
        country = request.env['res.country'].search([('id', '=', country_id)], limit=1)
        if (
            request.env.company.account_fiscal_country_id.code == "IN"
            and country.code == "IN"
            and (vat := address_values.get('vat')) and vat != partner_sudo.vat
        ):
            partner_sudo.action_l10n_in_verify_gstin_status(vat, ignore_errors=True)
        return invalid_fields, missing_fields, error_messages
