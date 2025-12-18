from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount


class L10nMYPortalAccount(PortalAccount):

    def _prepare_address_form_values(self, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(*args, **kwargs)

        l10n_my_identification_types = dict(request.env['res.partner']._fields['l10n_my_identification_type'].selection)
        # BRN applies only to companies. It must not be selectable for individuals, and it's enforced companies.
        l10n_my_identification_types.pop('BRN')
        default_classification = request.env.ref(
            'l10n_my_edi.class_00000', raise_if_not_found=False,
        )
        rendering_values.update({
            'l10n_my_identification_types': l10n_my_identification_types,
            'l10n_my_edi_industrial_classifications': request.env['l10n_my_edi.industry_classification'].sudo().search([]),
            'default_industrial_classification_id': default_classification.id if default_classification else False,
        })
        return rendering_values

    def _parse_form_data(self, form_data):
        address_values, extra_form_data = super()._parse_form_data(form_data)

        is_my_company = (
            request.env['res.country'].browse(address_values.get('country_id'))
            .exists().code == 'MY'
        )

        # MyInvois requires VAT, identification number and type; placeholders are used in certain cases which are handled below.
        if form_data.get('company_type') == 'person':
            if not address_values.get('l10n_my_edi_malaysian_tin') and address_values.get('l10n_my_identification_number'):
                address_values['l10n_my_edi_malaysian_tin'] = 'EI00000000010'

            if (
                not address_values.get('l10n_my_identification_number')
                and address_values.get('l10n_my_edi_malaysian_tin')
                and is_my_company
            ):
                address_values['l10n_my_identification_number'] = '000000000000'

        if form_data.get('company_type') == 'company':
            address_values['l10n_my_identification_type'] = 'BRN'
            if not is_my_company and not address_values['l10n_my_identification_number']:
                address_values['l10n_my_identification_number'] = '000000000000'
        return address_values, extra_form_data

    def _validate_address_values(self, address_values, partner_sudo, address_type, *args, **kwargs):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, partner_sudo, address_type, *args, **kwargs
        )

        _ = self.env._
        is_my_company = (
            request.env['res.country'].browse(address_values.get('country_id'))
            .exists().code == 'MY'
        )
        company_type = request.params.get('company_type')
        id_number = address_values.get('l10n_my_identification_number')
        id_type = address_values.get('l10n_my_identification_type')

        def _validate_required_fields(fields, message):
            missing = [field for field in fields if not address_values.get(field)]
            if missing:
                missing_fields.update(missing)
                error_messages.append(message)

        if id_number and (
            (id_type in ('NRIC', 'ARMY', 'PASSPORT') and len(id_number) > 12)
            or (id_type == 'BRN' and len(id_number) > 20)
        ):
            missing_fields.add('l10n_my_identification_number')
            error_messages.append(_("Please add a valid identification number"))

        if company_type == 'person':
            if is_my_company:
                if not id_number and not address_values.get('l10n_my_edi_malaysian_tin'):
                    _validate_required_fields(
                        ['l10n_my_identification_number', 'l10n_my_edi_malaysian_tin'],
                        _("Please provide at least an Identification Number or a TIN (Income Tax Number) to issue an invoice"),
                    )
            else:
                if (
                    not id_number
                    or id_type != 'PASSPORT'
                ):
                    error_messages.append(_("Some fields are missing or have wrong values"))
                    if not id_number:
                        missing_fields.add('l10n_my_identification_number')
                    if id_type != 'PASSPORT':
                        missing_fields.add('l10n_my_identification_type')

        elif company_type == 'company':
            if is_my_company:
                _validate_required_fields(
                    ['l10n_my_identification_number', 'vat'],
                    _("Please enter your Business Registration Number (BRN) and TIN (Income Tax Number) to proceed."),
                )
            else:
                _validate_required_fields(
                    ['l10n_my_edi_malaysian_tin'],
                    _("Malaysian VAT is required to process invoice"),
                )

        return invalid_fields, missing_fields, error_messages

    def _get_mandatory_address_fields(self, country_sudo):
        field_names = super()._get_mandatory_address_fields(country_sudo)

        if country_sudo.code == 'MY':
            field_names.add('state_id')

        return field_names
