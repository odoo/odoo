import re

from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount

L10N_SA_COMPANY_SCHEMES = {'CRN', 'MOM', 'MLS', '700', 'SAG', 'OTH'}


class L10nSAPortalAccount(PortalAccount):

    def _is_sa_company(self):
        return request.env.company.account_fiscal_country_id.code == 'SA'

    def _prepare_address_form_values(self, partner_sudo, *args, **kwargs):
        # EXTENDS portal
        rendering_values = super()._prepare_address_form_values(partner_sudo, *args, **kwargs)
        if self._is_sa_company():
            rendering_values['identification_schemes'] = dict(request.env['res.partner']._fields['l10n_sa_edi_additional_identification_scheme']._description_selection(request.env)).items()

        return rendering_values

    def _validate_address_values(self, address_values, partner_sudo, address_type, use_delivery_as_billing, *args, **kwargs):
        # EXTENDS portal
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, partner_sudo, address_type, use_delivery_as_billing, *args, **kwargs,
        )

        if (
            not self._is_sa_company()
            or (address_type != 'billing' and not use_delivery_as_billing)
            or request.env['res.country'].browse(int(address_values.get('country_id'))).code != 'SA'
        ):
            return invalid_fields, missing_fields, error_messages

        # Check if building number and plot identification are filled if vat is filled and are 4 digits
        check_fields = [
            'l10n_sa_edi_building_number',
            'l10n_sa_edi_plot_identification',
        ]

        for field in check_fields:
            field_val = address_values.get(field)
            if not field_val and address_values['vat']:
                missing_fields.add(field)
                error_messages.append(request.env._("%s needs to be filled since the VAT is filled", request.env['res.partner']._fields[field].string))
                continue

            if not re.fullmatch(r"\d{4}", field_val):
                invalid_fields.add(field)
                error_messages.append(request.env._("%s needs to be four digits", request.env['res.partner']._fields[field].string))

        if address_values.get('l10n_sa_edi_additional_identification_scheme') not in {'TIN', None} and not address_values.get('l10n_sa_edi_additional_identification_number'):
            # Special Case: identification number doesn't need to be filled if scheme is TIN
            missing_fields.add('l10n_sa_edi_additional_identification_number')
            error_messages.append(request.env._("Identification Number needs to be filled since the Identification Scheme is filled"))

        return invalid_fields, missing_fields, error_messages

    def _create_or_update_address(self, partner_sudo, address_type='billing', use_delivery_as_billing=False, **form_data):
        partner_sudo, url = super()._create_or_update_address(partner_sudo, address_type, use_delivery_as_billing, **form_data)

        if not self._is_sa_company() or (address_type != 'billing' and not use_delivery_as_billing):
            return partner_sudo, url

        is_sa_company_candidate = (
            partner_sudo.country_code == 'SA'
            and partner_sudo.commercial_partner_id == partner_sudo
            and partner_sudo.l10n_sa_edi_additional_identification_number
            and partner_sudo.l10n_sa_edi_additional_identification_scheme in L10N_SA_COMPANY_SCHEMES
        )

        partner_sudo.is_company = partner_sudo.vat or is_sa_company_candidate

        return partner_sudo, url
