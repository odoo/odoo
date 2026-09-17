# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.website_sale.controllers.main import WebsiteSale

L10N_ES_ID_TYPE_KEYS = ('ES_FOREIGN_ID', 'ES_PASSPORT', 'ES_RES_CERT', 'ES_OTHER_ID')
# VAT is folded into the same selector (the plain VAT field is hidden, see the
# `address_form_l10n_es_id_type` template), ahead of the alternative documents.
L10N_ES_ID_TYPE_SELECTOR_KEYS = ('vat',) + L10N_ES_ID_TYPE_KEYS


class WebsiteSaleL10nEsEcommerce(WebsiteSale):

    def _prepare_address_form_values(self, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(*args, **kwargs)

        if not rendering_values.get('is_used_as_billing') or self.env.company.country_code != 'ES':
            return rendering_values

        all_metadata = {
            'vat': {'label': rendering_values.get('vat_label') or self.env._('VAT')},
            **self.env['res.partner']._get_all_additional_identifiers_metadata(),
        }
        id_type_metadata = {
            key: all_metadata[key] for key in L10N_ES_ID_TYPE_SELECTOR_KEYS if key in all_metadata
        }
        partner = rendering_values['partner_sudo'] or rendering_values['current_partner']
        # Every submitted identifier is kept on the partner, switching type doesn't clear the
        # previous one. The form opens on the first one stored, in the selector's order.
        stored_identifiers = {'vat': partner.vat, **(partner.additional_identifiers or {})}
        current_key = next(
            (key for key in L10N_ES_ID_TYPE_SELECTOR_KEYS if stored_identifiers.get(key)),
            'vat',
        )
        current_value = stored_identifiers.get(current_key)
        rendering_values.update({
            # The selector's identifiers are kept by `_create_or_update_address`, don't also
            # render them as hidden inputs, the selected one would be submitted twice.
            'partner_additional_identifiers': {
                key: value
                for key, value in rendering_values.get('partner_additional_identifiers', {}).items()
                if key not in L10N_ES_ID_TYPE_KEYS
            },
            'l10n_es_id_type_metadata': id_type_metadata,
            'l10n_es_id_type_current_key': current_key,
            'l10n_es_id_type_current_value': current_value,
        })
        return rendering_values

    def _create_or_update_address(self, partner_sudo, *args, **form_data):
        # The ID-type selector submits a single identifier, while `_parse_form_data` rebuilds
        # `additional_identifiers` from the submitted keys only. Resubmit the other stored
        # identifiers so that only the selected one is set or cleared.
        if partner_sudo and 'l10n_es_id_type' in form_data:
            for key, value in (partner_sudo.additional_identifiers or {}).items():
                form_data.setdefault(key, value)
        return super()._create_or_update_address(partner_sudo, *args, **form_data)

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
        if not self.env['res.partner']._l10n_es_ecommerce_identification_required(country_sudo, state_sudo, order_sudo=kwargs.get('order_sudo')):
            return invalid_fields, missing_fields, error_messages

        identifiers = address_values.get('additional_identifiers') or {}
        has_identification = bool(address_values.get('vat')) or any(
            identifiers.get(key) for key in L10N_ES_ID_TYPE_KEYS
        )
        if not has_identification:
            id_type = kwargs.get('l10n_es_id_type')
            invalid_fields.add(id_type if id_type in L10N_ES_ID_TYPE_SELECTOR_KEYS else 'vat')
            error_messages.append(self.env._(
                "An identification document is required for this order. Select its type (VAT,"
                " foreign ID, passport, residence certificate...) next to the Company field and"
                " fill it in."
            ))

        return invalid_fields, missing_fields, error_messages
