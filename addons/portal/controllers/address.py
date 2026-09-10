# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import Controller, request, route
from odoo.tools import clean_context, single_email_re, str2bool
from odoo.tools.partner_identifiers import validation_error_message


class Address(Controller):

    @route('/my/addresses', type='http', auth='user', readonly=True, website=True)
    def my_addresses(self, **query_params):
        """Display the user's addresses."""
        partner_sudo = request.env.user.partner_id  # env.user is always sudoed
        address_data = self._prepare_address_data(partner_sudo, **query_params)
        has_invoice_type_address = any(
            address.type == 'invoice'
            for address in address_data['billing_addresses']
        )
        values = {
            'partner_sudo': partner_sudo,
            **address_data,
            'page_name': 'my_addresses',
            # One unique address
            'use_delivery_as_billing': not has_invoice_type_address,
            'address_url': '/my/address',
        }
        return request.render('portal.my_addresses', values)

    def _prepare_address_data(self, partner_sudo, **kwargs):
        """Provide the data of the current customer addresses.

        Gives the addresses the customer can use, including:
            * his own addresses
            * the addresses belonging to his commercial partner, if complete because
              he cannot edit those addresses.

        :param res.partner partner_sudo: The current user partner.
        :param dict kwargs: Forwarded to underlying methods and available for potential overrides.
        :return: A dictionary holding the current customer billing and delivery addresses.
        :rtype: dict
        """
        partner_sudo = partner_sudo.with_context(show_address=1)
        commercial_partner_sudo = partner_sudo.commercial_partner_id
        billing_partners_sudo = partner_sudo.search([
            ('id', 'child_of', commercial_partner_sudo.ids),
            '|',
            ('type', 'in', ['invoice', 'other']),
            ('id', '=', commercial_partner_sudo.id),
        ], order='id desc') | partner_sudo
        delivery_partners_sudo = partner_sudo.search(
            commercial_partner_sudo._get_delivery_address_domain(),
            order='id desc',
        ) | partner_sudo

        if partner_sudo != commercial_partner_sudo:  # Child of the commercial partner.
            # Don't display the commercial partner's addresses if they are not complete, as its
            # children can't edit them.
            if not commercial_partner_sudo._check_billing_address(**kwargs):
                billing_partners_sudo = billing_partners_sudo.filtered(
                    lambda p: p.id != commercial_partner_sudo.id
                )
            if not commercial_partner_sudo._check_delivery_address(**kwargs):
                delivery_partners_sudo = delivery_partners_sudo.filtered(
                    lambda p: p.id != commercial_partner_sudo.id
                )

        return {
            'billing_addresses': billing_partners_sudo,
            'delivery_addresses': delivery_partners_sudo,
        }

    @route(
        '/my/address',
        type='http',
        methods=['GET'],
        auth='user',
        website=True,
        sitemap=False,
        readonly=True,
    )
    def portal_address(
        self, partner_id=None, address_type='billing', use_delivery_as_billing=False, **query_params
    ):
        """ Display the address form.

        A partner and/or an address type can be given through the query string params to specify
        which address to update or create, and its type.

        :param str partner_id: The partner to update with the address form, if any, as a
            `res.partner` id.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param str use_delivery_as_billing: Whether the provided address should be used as both the
                                            delivery and the billing address. 'true' or 'false'.
        :param dict query_params: The additional query string parameters forwarded to
                                  `_prepare_address_form_values`.
        :return: The rendered address form.
        :rtype: str
        """
        partner_id = partner_id and int(partner_id)
        partner_sudo = request.env['res.partner'].with_context(show_address=1).sudo().browse(
            partner_id
        )

        if partner_sudo and not partner_sudo._can_be_edited_by_current_customer():
            raise Forbidden()

        address_form_values = {
            **self._prepare_address_form_values(
                partner_sudo,
                address_type=address_type,
                use_delivery_as_billing=str2bool(use_delivery_as_billing or 'false'),
                **query_params
            ),
            'page_name': 'address_form',
        }
        return request.render('portal.address_management', address_form_values)

    def _prepare_address_form_values(
        self, partner_sudo, address_type='billing', use_delivery_as_billing=False, callback='', **kwargs
    ):
        """Prepare the rendering values of the address form.

        :param partner_sudo: The partner whose address to update through the address form.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param bool use_delivery_as_billing: Whether the provided address should be used as both the
                                             billing and the delivery address.
        :param str callback: The URL to redirect to in case of successful address creation/update.
        :param dict kwargs: additional parameters, forwarded to other methods as well.
        :return: The address page values.
        :rtype: dict
        """
        current_partner = request.env['res.partner']._get_current_partner(**kwargs)
        commercial_partner = current_partner.commercial_partner_id  # handling commercial fields
        has_confirmed_documents = current_partner and current_partner._has_confirmed_documents()

        if partner_sudo:
            # When editing an existing address, display this record values, even if empty
            country_sudo = partner_sudo.country_id
            state_sudo = partner_sudo.state_id
            city_sudo = partner_sudo.city_id
            email = partner_sudo.email
            phone = partner_sudo.phone
            is_main_address = partner_sudo == current_partner
            is_main_contact = (
                is_main_address and current_partner._is_main_contact()
            )
        else:
            # When creating a new address, use existing customer values as default values
            country_sudo = current_partner.country_id or self._get_default_country(**kwargs)
            state_sudo = current_partner.state_id
            city_sudo = current_partner.city_id
            email = current_partner.email
            phone = current_partner.phone

            # Commercial fields can only be updated on main customer address, so they can only be
            # updated on new addresses if it's gonna be the customer main address
            is_main_address = not current_partner
            is_main_contact = not current_partner

        commercial_fields_warning = commercial_address_update_url = vat_warning = ""
        if not is_main_address:
            commercial_fields_warning = self.env._(
                "The company name and VAT number can only be updated on your main account."
            )
            commercial_address_update_url = "/my/account?redirect=/my/addresses"
        elif not is_main_contact:
            commercial_fields_warning = self.env._(
                "The company billing details can only be updated on the company account."
            )
        elif current_partner.vat and has_confirmed_documents:
            vat_warning = self.env._(
                "Updating VAT number is not allowed once document(s) have been issued for your"
                " account. Please contact us directly for this operation."
            )

        cities_data = (
            country_sudo._enforce_city_choice()
            and country_sudo._get_cities_data(state_sudo.id)
        )
        can_edit_country = not partner_sudo.country_id or partner_sudo._can_edit_country()
        country_warning = ""
        if not can_edit_country:
            country_warning = self.env._(
                "Changing country is not allowed once document(s) have been issued for your"
                " account. Please contact us directly for this operation."
            )

        return {
            'partner_sudo': partner_sudo,  # If set, customer is editing an existing address
            'partner_id': partner_sudo.id,
            'current_partner': current_partner,
            'commercial_partner': commercial_partner,
            'is_main_address': is_main_address,
            'discard_url': callback or '/my/addresses',
            'address_type': address_type,
            'can_edit_commercial_fields': not has_confirmed_documents and is_main_contact,
            'commercial_address_update_url': commercial_address_update_url,
            'commercial_fields_warning': commercial_fields_warning,
            'country_warning': country_warning,
            'callback': callback,
            'is_used_as_billing': address_type == 'billing' or use_delivery_as_billing,
            'required_fields': self.env['res.partner']._get_required_address_fields(
                address_type, country_sudo,
                use_delivery_as_billing=use_delivery_as_billing, **kwargs
            ),
            'use_delivery_as_billing': use_delivery_as_billing,
            'zip_applicability': country_sudo.zip_applicability,
            'zip_before_city': country_sudo._is_zip_before_city(),
            'vat_warning': vat_warning,
            'vat_label': country_sudo._get_vat_label(),

            # Form values
            'email': email,
            'phone': phone,
            'phone_code': f'+{country_sudo.phone_code}' if country_sudo.phone_code != 0 else '',
            'country': country_sudo,
            'countries': (
                request.env['res.country'].sudo().search([])
                if can_edit_country else country_sudo
            ),
            'state': state_sudo,
            'states': country_sudo.state_ids,
            'city': city_sudo,
            'cities_data': cities_data,
        }

    def _get_default_country(self, **kwargs):
        """ Get country of current user country as default. """
        return request.env.user.country_id

    @route(
        '/my/address/submit',
        type='http',
        methods=['POST'],
        auth='user',
        website=True,
        sitemap=False,
    )
    def portal_address_submit(self, partner_id=None, **form_data):
        """ Create or update an address from portal and redirect to appropriate page.

        If it succeeds, it returns the URL to redirect (client-side) to. If it fails (missing or
        invalid information), it highlights the problematic form input with the appropriate error
        message.

        :param str partner_id: The partner whose address to update with the address form, if any.
        :param dict form_data: The form data to process as address values.
        :return: A JSON-encoded feedback, with either the success URL or an error message.
        :rtype: str
        """
        partner_sudo = request.env['res.partner'].with_context(show_address=1).sudo().browse(
            partner_id and int(partner_id)
        )
        if partner_sudo and not partner_sudo._can_be_edited_by_current_customer():
            raise Forbidden()

        _partner_sudo, feedback_dict = self._create_or_update_address(partner_sudo, **form_data)

        return json.dumps(feedback_dict)

    @http.route('/my/profile/save', type='jsonrpc', auth='user', methods=['POST'], website=True)
    def save_edited_profile(self, user_id, image_1920):
        """ Save the edited profile image.

        :param int user_id: The identifier of the user whose profile is being edited.
        :param str image_1920: The new profile image in base64 format.
        :return: Boolean indicating whether the write operation was successful.
        :rtype: bool
        """
        if (user_id != request.env.user.id):
            raise UserError(self.env._("You cannot edit another user's profile."))
        return request.env.user.write({"image_1920": image_1920})

    def _create_or_update_address(
        self,
        partner_sudo,
        address_type='billing',
        use_delivery_as_billing=False,
        callback='/my/addresses',
        required_fields=False,
        verify_address_values=True,
        **form_data
    ):
        """ Create or update an address if there is no error else return error dict.

        :param str partner_id: The partner whose address to update with the address form, if any.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param dict form_data: The form data to process as address values.
        :param str use_delivery_as_billing: Whether the provided address should be used as both the
                                            billing and the delivery address. 'true' or 'false'.
        :param str callback: The URL to redirect to in case of successful address creation/update.
        :param str required_fields: The additional required address values, as a comma-separated
                                    list of `res.partner` fields.
        :param bool verify_address_values: Whether we want to check the given address values.
        :return: Partner record and A JSON-encoded feedback, with either the success URL or
                 an error message.
        :rtype: res.partner, dict
        """
        use_delivery_as_billing = str2bool(use_delivery_as_billing or 'false')

        # Parse form data into address values, and extract incompatible data as extra form data.
        address_values, extra_form_data = self._parse_form_data(form_data)

        if verify_address_values:
            # Validate the address values and highlights the problems in the form, if any.
            invalid_fields, missing_fields, error_messages = self._validate_address_values(
                address_values,
                partner_sudo,
                address_type,
                use_delivery_as_billing,
                required_fields or '',
                **extra_form_data,
            )
            if error_messages:
                return partner_sudo, {
                    'invalid_fields': list(invalid_fields | missing_fields),
                    'messages': error_messages,
                }

        parent_name_value = address_values.pop('parent_name', None)

        partner_context = clean_context(request.env.context)
        partner_context.update({
            "no_vat_validation": True,  # Already verified in _validate_address_values
        })

        if not partner_sudo:  # Creation of a new address.
            self._complete_address_values(
                address_values, address_type, use_delivery_as_billing, **form_data
            )
            partner_sudo = request.env['res.partner'].sudo().with_context(
                partner_context
            ).create(address_values)
            if hasattr(partner_sudo, '_onchange_phone_validation'):
                # The `phone_validation` module is installed.
                partner_sudo._onchange_phone_validation()
        elif not self._are_same_addresses(address_values, partner_sudo):
            # If name is not changed then pop it from the address_values, as it affects the bank account holder name
            if address_values['name'].strip() == (partner_sudo.name or '').strip():
                address_values.pop('name')
            # Keep the same partner if nothing changed.
            partner_sudo.with_context(partner_context).write(address_values)
            if 'phone' in address_values and hasattr(partner_sudo, '_onchange_phone_validation'):
                # The `phone_validation` module is installed.
                partner_sudo._onchange_phone_validation()

        if parent_name_value:
            if partner_sudo.commercial_partner_id != partner_sudo:
                if partner_sudo.commercial_partner_id.is_company:
                    parent_company = partner_sudo.commercial_partner_id
                    if parent_company.name != parent_name_value:
                        parent_company.name = parent_name_value
            elif (
                not partner_sudo.parent_id
                and partner_sudo.child_ids.filtered(lambda c: c.type == "contact")
            ):
                if partner_sudo.name != parent_name_value:
                    partner_sudo.name = parent_name_value
            else:  # Current partner is an individual with no parent
                # To check whether created parent company should have all the accounting related
                # details same as partner as in backend
                parent_company = partner_sudo.with_context(
                    partner_context
                )._create_parent_from_name(parent_name_value)
                parent_company.is_company = True

        self._handle_extra_form_data(extra_form_data, address_values)

        return partner_sudo, {'redirectUrl': callback}

    def _parse_form_data(self, form_data):
        """ Parse the form data and return them converted into address values and extra form data.

        :param dict form_data: The form data to convert to address values.
        :return: A tuple of converted address values and extra form data.
        :rtype: tuple[dict, dict]
        """
        address_values = {}
        extra_form_data = {}

        ResPartner = request.env['res.partner']
        partner_fields = ResPartner._fields
        authorized_partner_fields = request.env['res.partner']._get_frontend_writable_fields()
        all_additional_identifiers = request.env["res.partner"]._get_all_additional_identifiers_metadata()
        for key, value in form_data.items():
            if isinstance(value, str):
                value = value.strip()
            if key in partner_fields and key in authorized_partner_fields:
                field = partner_fields[key]
                if field.type == 'many2one' and isinstance(value, str) and value.isdigit():
                    address_values[key] = field.convert_to_cache(int(value), ResPartner)
                elif (
                    field.type == 'selection'
                    and value == ''  # noqa: PLC1901
                    and '' not in field.get_values(request.env)
                ):
                    # An empty string from an HTML select means "no selection"; map it to False.
                    address_values[key] = False
                else:
                    # Always keep field values, even if falsy, as it might be for resetting a field.
                    address_values[key] = field.convert_to_cache(value, ResPartner)
            elif (key_upper := key.upper()) in all_additional_identifiers:
                # Set the additional identifier values in the `additional_identifiers` field of the
                # address values. Empty values are dropped, which clears them on the partner.
                address_values.setdefault('additional_identifiers', {})
                if value:
                    address_values['additional_identifiers'][key_upper] = value
            elif value:  # The value cannot be saved on the `res.partner` model.
                extra_form_data[key] = value

        if 'zipcode' in form_data and not form_data.get('zip'):
            address_values['zip'] = form_data.pop('zipcode', '')

        country_id = address_values.get("country_id")
        country_sudo = request.env['res.country'].browse(country_id)
        if country_sudo._enforce_city_choice() and form_data.get("city_id"):
            if city := request.env["res.city"].browse(int(form_data["city_id"])):
                address_values["city"] = city.name

        return address_values, extra_form_data

    def _validate_address_values(
        self,
        address_values,
        partner_sudo,
        address_type,
        use_delivery_as_billing,
        required_fields,
        **kwargs,
    ):
        """ Validate the address values and return the invalid fields, the missing fields, and any
        error messages.

        :param dict address_values: The address values to validates.
        :param res.partner partner_sudo: The partner whose address values to validate, if any (can
                                         be empty).
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param bool use_delivery_as_billing: Whether the provided address should be used as both the billing and
                              the delivery address.
        :param str required_fields: The additional required address values, as a comma-separated
                                    list of `res.partner` fields.
        :param dict kwargs: Extra form data, available for overrides and some method calls.
        :return: The invalid fields, the missing fields, and any error messages.
        :rtype: tuple[set, set, list]
        """
        # data: values after preprocess
        invalid_fields = set()
        missing_fields = set()
        error_messages = []
        current_partner = request.env['res.partner']._get_current_partner(**kwargs)

        if partner_sudo:
            name_change = (
                'name' in address_values
                and partner_sudo.name
                and address_values['name'] != partner_sudo.name.strip()
            )
            country_change = (
                'country_id' in address_values
                and partner_sudo.country_id
                and address_values['country_id'] != partner_sudo.country_id.id
            )
            email_change = (
                'email' in address_values
                and partner_sudo.email
                and address_values['email'] != partner_sudo.email
            )

            # Prevent changing the partner country if documents have been issued.
            if country_change and not partner_sudo._can_edit_country():
                invalid_fields.add('country_id')
                error_messages.append(self.env._(
                    "Changing your country is not allowed once document(s) have been issued for your"
                    " account. Please contact us directly for this operation."
                ))

            # Prevent changing the partner name or email if it is an internal user.
            if (name_change or email_change) and not all(partner_sudo.user_ids.mapped('share')):
                if name_change:
                    invalid_fields.add('name')
                if email_change:
                    invalid_fields.add('email')
                error_messages.append(self.env._(
                    "If you are ordering for an external person, please place your order via the"
                    " backend. If you wish to change your name or email address, please do so in"
                    " the account settings or contact your administrator."
                ))

            def get_commercial_field_error_msg(field_description):
                if partner_sudo.commercial_partner_id.is_company:
                    return self.env._(
                        "The %(field_description)s is managed on your company account."
                    )
                elif current_partner != partner_sudo:
                    return self.env._(
                        "The %(field_description)s is managed on your main account address."
                    )
                else:
                    return self.env._(
                        "Changing %(field_description)s is not allowed once document(s) have been"
                        " issued for your account. Please contact us directly for this operation."
                    )

            # Prevent changing commercial fields on sub-addresses, as they are expected to match
            # commercial partner values, and would be reset if modified on the commercial partner.
            is_main_contact = (
                not current_partner
                or (partner_sudo == current_partner and current_partner._is_main_contact())
            )
            has_confirmed_documents = current_partner and current_partner._has_confirmed_documents()
            if not is_main_contact or has_confirmed_documents:
                commercial_fields = partner_sudo._commercial_fields()
                # The additional_identifiers field need to be handled separately, as it has multiple
                # values handled differently on the partner.
                commercial_fields.remove("additional_identifiers")
                for commercial_field_name in commercial_fields:
                    if commercial_field_name not in address_values:
                        continue
                    partner_sudo_field = partner_sudo._fields[commercial_field_name]
                    partner_sudo_value = partner_sudo_field.convert_to_cache(
                        partner_sudo[commercial_field_name],
                        partner_sudo,
                    )
                    # Allow to update commercial fields on individual addresses, if not set.
                    if is_main_contact and not bool(partner_sudo_value):
                        continue
                    if (
                        partner_sudo_value != address_values[commercial_field_name]
                        and (
                            bool(partner_sudo_value)
                            or bool(address_values[commercial_field_name])
                        )
                    ):
                        invalid_fields.add(commercial_field_name)
                        field_description = partner_sudo_field._description_string(request.env)
                        error_messages.append(get_commercial_field_error_msg(field_description))
                    else:
                        address_values.pop(commercial_field_name, None)

                for additional_identifier, value in address_values.get("additional_identifiers", {}).items():
                    partner_sudo_value = partner_sudo._get_additional_identifier(additional_identifier)
                    # Allow to update additional identifiers on individual addresses, if not set.
                    if is_main_contact and not bool(partner_sudo_value):
                        continue
                    if partner_sudo_value != value and (bool(partner_sudo_value) or bool(value)):
                        invalid_fields.add(additional_identifier)
                        error_messages.append(get_commercial_field_error_msg(additional_identifier))
                    else:
                        address_values["additional_identifiers"].pop(additional_identifier, None)

                # Company name shouldn't be updated anywhere but the main and company address, even
                # if it's not in the fields returned by _commercial_fields.
                if partner_sudo != request.env['res.partner']._get_current_partner(**kwargs):
                    address_values.pop('parent_name', None)
        else:
            # We're creating a new address, it'll only be the main address of public customers
            is_main_contact = not current_partner

        # Validate the email.
        if address_values.get('email') and not single_email_re.match(address_values['email']):
            invalid_fields.add('email')
            error_messages.append(self.env._("Invalid Email! Please enter a valid email address."))

        # Validate the VAT number.
        ResPartnerSudo = request.env['res.partner'].sudo()
        if (
            address_values.get('vat')
            and hasattr(ResPartnerSudo, '_check_vat')  # account module is installed
            and 'vat' not in invalid_fields
        ):
            partner_dummy = ResPartnerSudo.new({
                fname: address_values[fname]
                for fname in self._get_vat_validation_fields()
                if fname in address_values
            })
            try:
                partner_dummy._check_vat()
            except ValidationError as exception:
                invalid_fields.add('vat')
                error_messages.append(exception.args[0])

        # Validate additional_identifiers
        for additional_identifier, value in address_values.get("additional_identifiers", {}).items():
            validation_vals = self.env["res.partner"]._validate_identifier(
                additional_identifier, value
            )
            if not validation_vals["valid"]:
                invalid_fields.add(additional_identifier)
                identifier_label = self.env["res.partner"]._get_identifier_label(additional_identifier)
                error_messages.append(
                    validation_error_message(
                        self.env, identifier_label,
                        validation_vals["value"],
                        example=validation_vals["example"]
                    )
                )

        # Build the set of required fields from the address form's requirements.
        required_field_set = {f for f in required_fields.split(',') if f}

        # Complete the set of required fields based on the address type.
        country_id = address_values.get('country_id')
        country = request.env['res.country'].browse(country_id)
        required_field_set |= self.env["res.partner"]._get_required_address_fields(
            address_type, country, use_delivery_as_billing=use_delivery_as_billing, **kwargs
        )
        if (address_type == "billing" or use_delivery_as_billing) and not is_main_contact:
            commercial_fields = ResPartnerSudo._commercial_fields()
            for fname in commercial_fields:
                if fname in required_field_set and fname not in address_values:
                    required_field_set.remove(fname)

        address_fields = self.env["res.partner"]._get_mandatory_address_fields(country, **kwargs)
        if any(address_values.get(fname) for fname in address_fields):
            # If the customer provided any address information, they should provide their whole
            # address, even if the address wasn't required (e.g. the order only contains services).
            required_field_set |= address_fields

        # Verify that no required field has been left empty.
        for field_name in required_field_set:
            if not address_values.get(field_name):
                missing_fields.add(field_name)
        if missing_fields:
            error_messages.append(self.env._("Some required fields are empty."))

        return invalid_fields, missing_fields, error_messages

    def _get_vat_validation_fields(self):
        return {'country_id', 'vat'}

    def _complete_address_values(
        self, address_values, address_type, use_delivery_as_billing, **kwargs
    ):
        """ Complete the address values with the request's contextual values.

        :param dict address_values: The address values to complete.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param bool use_delivery_as_billing: Whether the provided address should be used as both the
                                             billing and the delivery address.
        :params **kwargs: Other contextual values.
        :return: None
        """
        address_values['lang'] = request.lang.code
        partner_sudo = request.env['res.partner']._get_current_partner(**kwargs)
        address_values['company_id'] = partner_sudo.company_id.id
        commercial_partner = partner_sudo.commercial_partner_id
        if use_delivery_as_billing:
            address_values['type'] = 'other'
        elif address_type == 'billing':
            address_values['type'] = 'invoice'
        elif address_type == 'delivery':
            address_values['type'] = 'delivery'

        # Avoid linking the address to the default archived 'Public user' partner.
        if commercial_partner.active:
            address_values['parent_id'] = commercial_partner.id

    def _are_same_addresses(self, address_values, partner):
        ResPartner = request.env['res.partner']
        for key, new_val in address_values.items():
            val = ResPartner._fields[key].convert_to_cache(partner[key], ResPartner)
            if new_val != val and (val or new_val):
                # Skip falsy values if unset in values and on record
                return False
        return True

    def _handle_extra_form_data(self, extra_form_data, address_values):
        """ Handling extra form data that were not processed on the address from.

        :param dict extra_form_data: The extra form data.
        :param dict address_values: The address value.
        :return: None
        """

    @route(
        '/my/address/country_info/<model("res.country"):country>',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
        readonly=True,
    )
    def portal_address_country_info(self, country, address_type, **kwargs):
        address_fields = country._get_address_fields()
        required_fields = self.env['res.partner']._get_required_address_fields(
            address_type, country, **kwargs
        )
        state_data = self.env['res.country.state'].sudo().search_read(
            [('country_id', '=', country.id)],
            ['id', 'name', 'code'],
        )
        cities_data = []
        if 'city_id' in required_fields and not country.state_required:
            # If country enforces states, cities will be fetched through the state_info route
            # depending on the chosen state.
            cities_data = country._get_cities_data()

        return {
            'address_fields': address_fields,
            'required_fields': list(required_fields),
            'zip_before_city': country._is_zip_before_city(default_address_fields=address_fields),
            'selection': {
                'state_id': state_data,
                'city_id': cities_data,
            },
            'phone_code': f'+{country.phone_code}' if country.phone_code != 0 else '',
            'vat_label': country._get_vat_label(),
        }

    @route(
        '/my/address/state_info/',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
        readonly=True,
    )
    def portal_address_state_info(self, country_id, state_id=False, **kw):
        """Return the cities of the selected state, or all cities of the country when no state is
        provided"""
        country_sudo = self.env['res.country'].browse(country_id).sudo()
        if country_sudo._enforce_city_choice():
            return {
                'cities': country_sudo._get_cities_data(state_id=state_id),
            }

        return {}

    @route('/my/address/archive', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def address_archive(self, partner_id):
        address_sudo = request.env['res.partner'].sudo().browse(int(partner_id)).exists()
        if not address_sudo or not address_sudo._can_be_edited_by_current_customer():
            raise Forbidden()

        if address_sudo == request.env.user.partner_id:
            raise UserError(self.env._("You cannot archive your main address"))

        address_sudo.action_archive()
