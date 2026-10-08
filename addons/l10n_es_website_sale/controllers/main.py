# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.http import request, route
from odoo.addons.website_sale.controllers.main import WebsiteSale

# Rendered as a single ID-type selector + value field next to "Company" (see
# `_prepare_address_form_values`) rather than through the generic "Add identifier"
# dropdown, so they're excluded from the latter to avoid duplicating them.
L10N_ES_ID_TYPE_KEYS = ('ES_FOREIGN_ID', 'ES_PASSPORT', 'ES_RES_CERT', 'ES_OTHER_ID')
# VAT is folded into the same selector (the plain VAT field is hidden, see the
# `address_form_l10n_es_id_type` template), ahead of the alternative documents.
L10N_ES_ID_TYPE_SELECTOR_KEYS = ('vat',) + L10N_ES_ID_TYPE_KEYS


class WebsiteSaleL10nEsEcommerce(WebsiteSale):

    @route()
    def portal_address_country_info(self, country, address_type, **kw):
        # The country-change refresh route doesn't forward the cart, which the
        # simplified-invoice VAT relaxation needs to read the order total.
        # Inject it here so the model stays free of any `request` dependency.
        kw.setdefault('order_sudo', request.cart)
        return super().portal_address_country_info(country, address_type, **kw)

    def _get_checkout_additional_identifiers_metadata(self, country):
        metadata = super()._get_checkout_additional_identifiers_metadata(country)
        return {key: value for key, value in metadata.items() if key not in L10N_ES_ID_TYPE_KEYS}

    def _prepare_address_form_values(self, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(*args, **kwargs)

        if not rendering_values.get('is_used_as_billing') or self.env.company.country_code != 'ES':
            return rendering_values

        all_metadata = {
            'vat': {'label': rendering_values.get('vat_label') or 'VAT'},
            **self.env['res.partner']._get_all_additional_identifiers_metadata(),
        }
        id_type_metadata = {
            key: all_metadata[key] for key in L10N_ES_ID_TYPE_SELECTOR_KEYS if key in all_metadata
        }
        current_partner = rendering_values.get('current_partner')
        stored_identifiers = (current_partner.additional_identifiers or {}) if current_partner else {}
        current_vat = current_partner.vat if current_partner else False
        if current_vat:
            current_key = 'vat'
        else:
            current_key = next(
                (key for key in L10N_ES_ID_TYPE_KEYS if stored_identifiers.get(key)),
                'vat',
            )
        current_value = current_vat if current_key == 'vat' else stored_identifiers.get(current_key)
        rendering_values.update({
            'l10n_es_id_type_metadata': id_type_metadata,
            'l10n_es_id_type_current_key': current_key,
            'l10n_es_id_type_current_value': current_value,
        })
        return rendering_values

    def _validate_address_values(
        self, address_values, partner_sudo, address_type, use_delivery_as_billing, required_fields, **kwargs
    ):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, partner_sudo, address_type, use_delivery_as_billing, required_fields, **kwargs
        )

        if self.env.company.country_code != 'ES' or not (address_type == 'billing' or use_delivery_as_billing):
            return invalid_fields, missing_fields, error_messages

        country_sudo = self.env['res.country'].sudo().browse(address_values.get('country_id'))
        state_sudo = self.env['res.country.state'].sudo().browse(address_values.get('state_id'))
        if not self.env['res.partner']._l10n_es_ecommerce_identification_required(country_sudo, state_sudo):
            return invalid_fields, missing_fields, error_messages

        identifiers = address_values.get('additional_identifiers') or {}
        has_identification = bool(address_values.get('vat')) or any(
            identifiers.get(key) for key in L10N_ES_ID_TYPE_KEYS
        )
        if not has_identification:
            error_messages.append(self.env._(
                "Outside of Spain VAT territory an ID type is required"
                ". Select (VAT, foreign ID, passport, residence certificate...) and fill it in,"
                " next to the Company field."
            ))

        return invalid_fields, missing_fields, error_messages
