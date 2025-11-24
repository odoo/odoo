# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import math
import re

from werkzeug import urls
from werkzeug.exceptions import Forbidden

from odoo import SUPERUSER_ID, _, http
from odoo.exceptions import AccessDenied, AccessError, MissingError, UserError, ValidationError
from odoo.http import Controller, content_disposition, request, route
from odoo.tools import clean_context, consteq, single_email_re, str2bool
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

# --------------------------------------------------
# Misc tools
# --------------------------------------------------

def pager(url, total, page=1, step=30, scope=5, url_args=None):
    """ Generate a dict with required value to render `website.pager` template.

    This method computes url, page range to display, ... in the pager.

    Enhanced pager logic for SEO optimization:
    - Shows first and last page in pagination
    - Shows current page with -1 and +1 neighbors
    - Adds ellipses when necessary

    :param str url : base url of the page link
    :param int total : number total of item to be splitted into pages
    :param int page : current page
    :param int step : item per page
    :param int scope : number of page to display on pager
    :param dict url_args : additionnal parameters to add as query params to page url
    :returns dict
    """
    # Compute Pager
    page_count = int(math.ceil(float(total) / step))

    page = max(1, min(int(page if str(page).isdigit() else 1), page_count))

    page_previous = max(1, page - 1)
    page_next = min(page_count, page + 1)

    def get_url(page):
        _url = "%s/page/%s" % (url, page) if page > 1 else url
        if url_args:
            _url = "%s?%s" % (_url, urls.url_encode(url_args))
        return _url

    # Build page list based on conditions
    if page_count <= 5:
        page_list = list(range(1, page_count + 1))
    elif page <= 3:
        page_list = [1, 2, 3, 4, "…", page_count]
    elif page >= page_count - 2:
        page_list = [1, "…"] + list(range(page_count - 3, page_count + 1))
    else:
        page_list = [1, "…", page - 1, page, page + 1, "…", page_count]

    pages = [
        {"num": p, "url": get_url(p) if p != "…" else None, "is_current": p == page}
        for p in page_list
    ]

    return {
        "page_count": page_count,
        "offset": (page - 1) * step,
        "page": {
            'url': get_url(page),
            'num': page
        },
        "page_first": {
            'url': get_url(1),
            'num': 1
        },
        "page_previous": {
            'url': get_url(page_previous),
            'num': page_previous
        },
        "page_next": {
            'url': get_url(page_next),
            'num': page_next
        },
        "page_last": {
            'url': get_url(page_count),
            'num': page_count
        },
        "pages": pages
    }


def get_records_pager(ids, current):
    if current.id in ids and (hasattr(current, 'website_url') or hasattr(current, 'access_url')):
        attr_name = 'access_url' if hasattr(current, 'access_url') else 'website_url'
        idx = ids.index(current.id)
        prev_record = idx != 0 and current.browse(ids[idx - 1])
        next_record = idx < len(ids) - 1 and current.browse(ids[idx + 1])

        if prev_record and prev_record[attr_name] and attr_name == "access_url":
            prev_url = '%s?access_token=%s' % (prev_record[attr_name], prev_record._portal_ensure_token())
        elif prev_record and prev_record[attr_name]:
            prev_url = prev_record[attr_name]
        else:
            prev_url = prev_record

        if next_record and next_record[attr_name] and attr_name == "access_url":
            next_url = '%s?access_token=%s' % (next_record[attr_name], next_record._portal_ensure_token())
        elif next_record and next_record[attr_name]:
            next_url = next_record[attr_name]
        else:
            next_url = next_record

        return {
            'prev_record': prev_url,
            'next_record': next_url,
        }
    return {}


def _build_url_w_params(url_string, query_params, remove_duplicates=True):
    """ Rebuild a string url based on url_string and correctly compute query parameters
    using those present in the url and those given by query_params. Having duplicates in
    the final url is optional. For example:

     * url_string = '/my?foo=bar&error=pay'
     * query_params = {'foo': 'bar2', 'alice': 'bob'}
     * if remove duplicates: result = '/my?foo=bar2&error=pay&alice=bob'
     * else: result = '/my?foo=bar&foo=bar2&error=pay&alice=bob'
    """
    url = urls.url_parse(url_string)
    url_params = url.decode_query()
    if remove_duplicates:  # convert to standard dict instead of werkzeug multidict to remove duplicates automatically
        url_params = url_params.to_dict()
    url_params.update(query_params)
    return url.replace(query=urls.url_encode(url_params)).to_url()


class CustomerPortal(Controller):

    _items_per_page = 80

    def _prepare_portal_layout_values(self):
        """Values for /my/* templates rendering.

        Does not include the record counts.
        """
        # get customer sales rep
        sales_user_sudo = request.env['res.users']
        partner_sudo = request.env.user.partner_id
        if partner_sudo.user_id and not partner_sudo.user_id._is_public():
            sales_user_sudo = partner_sudo.user_id
        else:
            fallback_sales_user = partner_sudo.commercial_partner_id.user_id
            if fallback_sales_user and not fallback_sales_user._is_public():
                sales_user_sudo = fallback_sales_user

        return {
            'sales_user': sales_user_sudo,
            'page_name': 'home',
        }

    def _prepare_home_portal_values(self, counters):
        """Values for /my & /my/home routes template rendering.

        Includes the record count for the displayed badges.
        where 'counters' is the list of the displayed badges
        and so the list to compute.
        """
        return {}

    @route(['/my/counters'], type='jsonrpc', auth="user", website=True, readonly=True)
    def counters(self, counters, **kw):
        cache = request.session.get('portal_counters', {}).copy()
        res = self._prepare_home_portal_values(counters)
        cache.update({k: bool(v) for k, v in res.items() if k.endswith('_count')})
        if cache != request.session.get('portal_counters'):
            request.session['portal_counters'] = cache
        return res

    @route(['/my', '/my/home'], type='http', auth="user", website=True, list_as_website_content=_lt("User Dashboard"))
    def home(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update(self._prepare_home_portal_values([]))
        return request.render("portal.portal_my_home", values)

    @route(['/my/account'], type='http', auth='user', website=True)
    def account(self, **kwargs):
        response = request.render(
            'portal.portal_my_details',
            self._prepare_my_account_rendering_values(**kwargs),
        )
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    def _prepare_my_account_rendering_values(self, redirect='/my', **kwargs):
        """ Prepare the rendering values for the /my/account route template.

        :param str redirect: route to redirect to after the address update
        :param dict kwargs: unused parameters available for overrides
        :return: The rendering values
        :rtype: dict
        """
        return {
            'page_name': 'my_details',
            **self._prepare_portal_layout_values(),
            **self._prepare_address_form_values(
                partner_sudo=request.env.user.partner_id,
                # Main address should always have delivery & billing information set
                use_delivery_as_billing=True,
                callback=redirect,
            ),
        }

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

    def _prepare_address_data(self, partner_sudo, **_kwargs):
        """Provide the data of the current customer addresses.

        Gives the addresses the customer can use, including:
            * his own addresses
            * the addresses belonging to his commercial partner, if complete because
              he cannot edit those addresses.

        :param res.partner partner_sudo: The current user partner.
        :param dict _kwargs: unused parameters available for potential overrides.
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
            if not self._check_billing_address(commercial_partner_sudo):
                billing_partners_sudo = billing_partners_sudo.filtered(
                    lambda p: p.id != commercial_partner_sudo.id
                )
            if not self._check_delivery_address(commercial_partner_sudo):
                delivery_partners_sudo = delivery_partners_sudo.filtered(
                    lambda p: p.id != commercial_partner_sudo.id
                )

        return {
            'billing_addresses': billing_partners_sudo,
            'delivery_addresses': delivery_partners_sudo,
        }

    def _check_billing_address(self, partner_sudo):
        """ Check that all mandatory billing fields are filled for the given partner.

        :param res.partner partner_sudo: The partner whose billing address to check.
        :return: Whether all mandatory fields are filled.
        :rtype: bool
        """
        mandatory_billing_fields = self._get_mandatory_billing_address_fields(
            partner_sudo.country_id
        )
        return all(partner_sudo.read(mandatory_billing_fields)[0].values())

    def _get_mandatory_billing_address_fields(self, country_sudo):
        """ Return the set of mandatory billing field names.

        :param res.country country_sudo: The country to use to build the set of mandatory fields.
        :return: The set of mandatory billing field names.
        :rtype: set
        """
        base_fields = {'name', 'email'}
        if not self._needs_address():
            return base_fields
        base_fields.add('phone')  # not required for quick checkout (event)
        return base_fields | self._get_mandatory_address_fields(country_sudo)

    def _check_delivery_address(self, partner_sudo):
        """ Check that all mandatory delivery fields are filled for the given partner.

        :param res.partner partner_sudo: The partner whose delivery address to check.
        :return: Whether all mandatory fields are filled.
        :rtype: bool
        """
        mandatory_delivery_fields = self._get_mandatory_delivery_address_fields(
            partner_sudo.country_id
        )
        return all(partner_sudo.read(mandatory_delivery_fields)[0].values())

    def _get_mandatory_delivery_address_fields(self, country_sudo):
        """ Return the set of mandatory delivery field names.

        :param res.country country_sudo: The country to use to build the set of mandatory fields.
        :return: The set of mandatory delivery field names.
        :rtype: set
        """
        base_fields = {'name', 'email'}
        if not self._needs_address():
            return base_fields
        base_fields.add('phone')  # not required for quick checkout (event)
        return base_fields | self._get_mandatory_address_fields(country_sudo)

    def _needs_address(self):
        """ Hook meant to be overridden in other modules. """
        return True

    def _get_mandatory_address_fields(self, country_sudo):
        """ Return the set of common mandatory address fields.

        :param res.country country_sudo: The country to use to build the set of mandatory fields.
        :return: The set of common mandatory address field names.
        :rtype: set
        """
        field_names = {'street', 'city', 'country_id'}
        if country_sudo.state_required:
            field_names.add('state_id')
        if country_sudo.zip_required:
            field_names.add('zip')
        return field_names

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

        # TODO in the future: rename can_edit_vat
        # Means something like 'can edit commercial fields on current address'
        if partner_sudo:
            # Existing address, use the values defined on the address
            state_id = partner_sudo.state_id.id
            country_sudo = partner_sudo.country_id
            can_edit_vat = partner_sudo.can_edit_vat()
        else:
            # New address, take default values from current partner
            country_sudo = current_partner.country_id or self._get_default_country(**kwargs)
            state_id = current_partner.state_id.id
            can_edit_vat = not current_partner or (
                partner_sudo == current_partner and current_partner.can_edit_vat()
            )
        address_fields = (country_sudo and country_sudo.get_address_fields()) or ['city', 'zip']

        return {
            'partner_sudo': partner_sudo,  # If set, customer is editing an existing address
            'partner_id': partner_sudo.id,
            'current_partner': current_partner,
            'commercial_partner': current_partner.commercial_partner_id,
            'is_commercial_address': not current_partner or partner_sudo == commercial_partner,
            'is_main_address': not current_partner or (partner_sudo and partner_sudo == current_partner),
            'commercial_address_update_url': (
                # Only redirect to account update if the logged in user is their own commercial
                # partner.
                current_partner == commercial_partner and "/my/account?redirect=/my/addresses"
            ),
            'address_type': address_type,
            'can_edit_vat': can_edit_vat,
            'can_edit_country': not partner_sudo.country_id or partner_sudo._can_edit_country(),
            'callback': callback,
            'country': country_sudo,
            'countries': request.env['res.country'].sudo().search([]),
            'is_used_as_billing': address_type == 'billing' or use_delivery_as_billing,
            'use_delivery_as_billing': use_delivery_as_billing,
            'state_id': state_id,
            'country_states': country_sudo.state_ids,
            'zip_before_city': (
                'zip' in address_fields
                and address_fields.index('zip') < address_fields.index('city')
            ),
            'vat_label': request.env._("VAT"),
            'discard_url': callback or '/my/addresses',
        }

    def _is_used_as_billing(self, address_type, **kwargs):
        return address_type == 'billing'

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

        if not partner_sudo:  # Creation of a new address.
            self._complete_address_values(
                address_values, address_type, use_delivery_as_billing, **form_data
            )
            create_context = clean_context(request.env.context)
            create_context.update({
                'tracking_disable': True,
                'no_vat_validation': True,  # Already verified in _validate_address_values
            })
            partner_sudo = request.env['res.partner'].sudo().with_context(
                create_context
            ).create(address_values)
            if hasattr(partner_sudo, '_onchange_phone_validation'):
                # The `phone_validation` module is installed.
                partner_sudo._onchange_phone_validation()
        elif not self._are_same_addresses(address_values, partner_sudo):
            # If name is not changed then pop it from the address_values, as it affects the bank account holder name
            if address_values['name'].strip() == (partner_sudo.name or '').strip():
                address_values.pop('name')
            partner_sudo.write(address_values)  # Keep the same partner if nothing changed.
            if 'phone' in address_values and hasattr(partner_sudo, '_onchange_phone_validation'):
                # The `phone_validation` module is installed.
                partner_sudo._onchange_phone_validation()

        if (
            'company_name' in address_values
            and partner_sudo.commercial_partner_id != partner_sudo
            and partner_sudo.commercial_partner_id.is_company
        ):
            # If partner is an individual, update existing company's name or remove one
            company_name = address_values['company_name']
            parent_company = partner_sudo.commercial_partner_id
            partner_sudo.company_name = False

            if company_name and parent_company and parent_company.name != company_name:
                parent_company.name = company_name

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
        for key, value in form_data.items():
            if isinstance(value, str):
                value = value.strip()
            if key in partner_fields and key in authorized_partner_fields:
                field = partner_fields[key]
                if field.type == 'many2one' and isinstance(value, str) and value.isdigit():
                    address_values[key] = field.convert_to_cache(int(value), ResPartner)
                else:
                    # Always keep field values, even if falsy, as it might be for resetting a field.
                    address_values[key] = field.convert_to_cache(value, ResPartner)
            elif value:  # The value cannot be saved on the `res.partner` model.
                extra_form_data[key] = value

        if 'zipcode' in form_data and not form_data.get('zip'):
            address_values['zip'] = form_data.pop('zipcode', '')

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
                error_messages.append(_(
                    "Changing your country is not allowed once document(s) have been issued for your"
                    " account. Please contact us directly for this operation."
                ))

            # Prevent changing the partner name or email if it is an internal user.
            if (name_change or email_change) and not all(partner_sudo.user_ids.mapped('share')):
                if name_change:
                    invalid_fields.add('name')
                if email_change:
                    invalid_fields.add('email')
                error_messages.append(_(
                    "If you are ordering for an external person, please place your order via the"
                    " backend. If you wish to change your name or email address, please do so in"
                    " the account settings or contact your administrator."
                ))

            # Prevent changing commercial fields on sub-addresses, as they are expected to match
            # commercial partner values, and would be reset if modified on the commercial partner.
            if not (is_commercial_address := partner_sudo == partner_sudo.commercial_partner_id):
                for commercial_field_name in partner_sudo._commercial_fields():
                    if (
                        commercial_field_name in address_values
                        and partner_sudo[commercial_field_name] != address_values[commercial_field_name]
                        and (
                            bool(partner_sudo[commercial_field_name])
                            or bool(address_values[commercial_field_name])
                        )
                    ):
                        invalid_fields.add(commercial_field_name)
                        field_description = partner_sudo._fields[commercial_field_name]._description_string(request.env)
                        if partner_sudo.commercial_partner_id.is_company:
                            error_messages.append(_(
                                "The %(field_name)s is managed on your company account.",
                                field_name=field_description,
                            ))
                        else:
                            error_messages.append(_(
                                "The %(field_name)s is managed on your main account address.",
                                field_name=field_description,
                            ))
                    else:
                        address_values.pop(commercial_field_name, None)

                # Company name shouldn't be updated anywhere but the main and company address, even
                # if it's not in the fields returned by _commercial_fields.
                if partner_sudo != request.env['res.partner']._get_current_partner(**kwargs):
                    address_values.pop('company_name', None)
            # Prevent changing the VAT number on a commercial partner if documents have been issued.
            elif (
                'vat' in address_values
                and partner_sudo.vat
                and address_values['vat'] != partner_sudo.vat
                and not partner_sudo.can_edit_vat()
            ):
                invalid_fields.add('vat')
                error_messages.append(_(
                    "Changing VAT number is not allowed once document(s) have been issued for your"
                    " account. Please contact us directly for this operation."
                ))
        else:
            # We're creating a new address, it'll only be the main address of public customers
            is_commercial_address = not request.env['res.partner']._get_current_partner(**kwargs)

        # Validate the email.
        if address_values.get('email') and not single_email_re.match(address_values['email']):
            invalid_fields.add('email')
            error_messages.append(_("Invalid Email! Please enter a valid email address."))

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

        # Build the set of required fields from the address form's requirements.
        required_field_set = {f for f in required_fields.split(',') if f}

        # Complete the set of required fields based on the address type.
        country_id = address_values.get('country_id')
        country = request.env['res.country'].browse(country_id)
        if address_type == 'delivery' or use_delivery_as_billing:
            required_field_set |= self._get_mandatory_delivery_address_fields(country)
        if address_type == 'billing' or use_delivery_as_billing:
            required_field_set |= self._get_mandatory_billing_address_fields(country)
            if not is_commercial_address:
                commercial_fields = ResPartnerSudo._commercial_fields()
                for fname in commercial_fields:
                    if fname in required_field_set and fname not in address_values:
                        required_field_set.remove(fname)

        address_fields = self._get_mandatory_address_fields(country)
        if any(address_values.get(fname) for fname in address_fields):
            # If the customer provided any address information, they should provide their whole
            # address, even if the address wasn't required (e.g. the order only contains services).
            required_field_set |= address_fields

        # Verify that no required field has been left empty.
        for field_name in required_field_set:
            if not address_values.get(field_name):
                missing_fields.add(field_name)
        if missing_fields:
            error_messages.append(_("Some required fields are empty."))

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
        partner = request.env['res.partner']._get_current_partner(**kwargs)
        address_values['company_id'] = partner.company_id.id
        commercial_partner = partner.commercial_partner_id
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
    def portal_address_country_info(self, country, address_type, **kw):
        address_fields = country.get_address_fields()
        if address_type == 'billing':
            required_fields = self._get_mandatory_billing_address_fields(country)
        else:
            required_fields = self._get_mandatory_delivery_address_fields(country)
        return {
            'fields': address_fields,
            'zip_before_city': (
                'zip' in address_fields
                and address_fields.index('zip') < address_fields.index('city')
            ),
            'states': [(st.id, st.name, st.code) for st in country.sudo().state_ids],
            'phone_code': country.phone_code,
            'required_fields': list(required_fields),
        }

    @route('/my/address/archive', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def address_archive(self, partner_id):
        address_sudo = request.env['res.partner'].sudo().browse(int(partner_id)).exists()
        if not address_sudo or not address_sudo._can_be_edited_by_current_customer():
            raise Forbidden()

        if address_sudo == request.env.user.partner_id:
            raise UserError(_("You cannot archive your main address"))

        address_sudo.action_archive()

    # Security

    @route('/my/security', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def security(self, **post):
        values = self._prepare_portal_layout_values()
        values['get_error'] = get_error
        values['allow_api_keys'] = bool(request.env['ir.config_parameter'].sudo().get_param('portal.allow_api_keys'))
        values['open_deactivate_modal'] = False

        if request.httprequest.method == 'POST':
            values.update(self._update_password(
                post['old'].strip(),
                post['new1'].strip(),
                post['new2'].strip()
            ))

        return request.render('portal.portal_my_security', values, headers={
            'X-Frame-Options': 'SAMEORIGIN',
            'Content-Security-Policy': "frame-ancestors 'self'"
        })

    def _update_password(self, old, new1, new2):
        for k, v in [('old', old), ('new1', new1), ('new2', new2)]:
            if not v:
                return {'errors': {'password': {k: _("You cannot leave any password empty.")}}}

        if new1 != new2:
            return {'errors': {'password': {'new2': _("The new password and its confirmation must be identical.")}}}

        try:
            request.env['res.users'].change_password(old, new1)
        except AccessDenied as e:
            msg = e.args[0]
            if msg == AccessDenied().args[0]:
                msg = _('The old password you provided is incorrect, your password was not changed.')
            return {'errors': {'password': {'old': msg}}}
        except UserError as e:
            return {'errors': {'password': str(e)}}

        # update session token so the user does not get logged out (cache cleared by passwd change)
        new_token = request.env.user._compute_session_token(request.session.sid)
        request.session.session_token = new_token

        return {'success': {'password': True}}

    @route('/my/deactivate_account', type='http', auth='user', website=True, methods=['POST'])
    def deactivate_account(self, validation, password, **post):
        values = self._prepare_portal_layout_values()
        values['get_error'] = get_error
        values['open_deactivate_modal'] = True
        credential = {'login': request.env.user.login, 'password': password, 'type': 'password'}

        if validation != request.env.user.login:
            values['errors'] = {'deactivate': 'validation'}
        else:
            try:
                request.env['res.users']._check_credentials(credential, {'interactive': True})
                request.env.user.sudo()._deactivate_portal_user(**post)
                request.session.logout()
                return request.redirect('/web/login?message=%s' % urls.url_quote(_('Account deleted!')))
            except AccessDenied:
                values['errors'] = {'deactivate': 'password'}
            except UserError as e:
                values['errors'] = {'deactivate': {'other': str(e)}}

        return request.render('portal.portal_my_security', values, headers={
            'X-Frame-Options': 'SAMEORIGIN',
            'Content-Security-Policy': "frame-ancestors 'self'",
        })

    @http.route('/portal/attachment/remove', type='jsonrpc', auth='public')
    def attachment_remove(self, attachment_id, access_token=None):
        """Remove the given `attachment_id`, only if it is in a "pending" state.

        The user must have access right on the attachment or provide a valid
        `access_token`.
        """
        try:
            attachment_sudo = self._document_check_access('ir.attachment', int(attachment_id), access_token=access_token)
        except (AccessError, MissingError) as e:
            raise UserError(_("The attachment does not exist or you do not have the rights to access it."))

        if attachment_sudo.res_model != 'mail.compose.message' or attachment_sudo.res_id != 0:
            raise UserError(_("The attachment %s cannot be removed because it is not in a pending state.", attachment_sudo.name))

        if attachment_sudo.env['mail.message'].search_count([('attachment_ids', 'in', attachment_sudo.ids)], limit=1):
            raise UserError(_("The attachment %s cannot be removed because it is linked to a message.", attachment_sudo.name))

        return attachment_sudo.unlink()

    # Bussiness Methods

    def _document_check_access(self, model_name, document_id, access_token=None):
        """Check if current user is allowed to access the specified record.

        :param str model_name: model of the requested record
        :param int document_id: id of the requested record
        :param str access_token: record token to check if user isn't allowed to read requested record
        :return: expected record, SUDOED, with SUPERUSER context
        :raise MissingError: record not found in database, might have been deleted
        :raise AccessError: current user isn't allowed to read requested document (and no valid token was given)
        """
        document = request.env[model_name].browse([document_id])
        document_sudo = document.with_user(SUPERUSER_ID).exists()
        if not document_sudo:
            raise MissingError(_("This document does not exist."))
        try:
            document.check_access('read')
        except AccessError:
            if not access_token or not document_sudo.access_token or not consteq(document_sudo.access_token, access_token):
                raise
        return document_sudo

    def _get_page_view_values(self, document, access_token, values, session_history, no_breadcrumbs, **kwargs):
        """Include necessary values for portal chatter & pager setup (see template portal.message_thread).

        :param document: record to display on portal
        :param str access_token: provided document access token
        :param dict values: base dict of values where chatter rendering values should be added
        :param str session_history: key used to store latest records browsed on the portal in the session
        :param bool no_breadcrumbs:
        :return: updated values
        :rtype: dict
        """
        values['object'] = document

        if access_token:
            # if no_breadcrumbs = False -> force breadcrumbs even if access_token to `invite` users to register if they click on it
            values['no_breadcrumbs'] = no_breadcrumbs
            values['access_token'] = access_token
            values['token'] = access_token  # for portal chatter

        # Those are used notably whenever the payment form is implied in the portal.
        if kwargs.get('error'):
            values['error'] = kwargs['error']
        if kwargs.get('warning'):
            values['warning'] = kwargs['warning']
        if kwargs.get('success'):
            values['success'] = kwargs['success']
        # Email token for posting messages in portal view with identified author
        if kwargs.get('pid'):
            values['pid'] = kwargs['pid']
        if kwargs.get('hash'):
            values['hash'] = kwargs['hash']

        history = request.session.get(session_history, [])
        values.update(get_records_pager(history, document))

        return values

    def _show_report(self, model, report_type, report_ref, download=False):
        if report_type not in ('html', 'pdf', 'text'):
            raise UserError(_("Invalid report type: %s", report_type))

        ReportAction = request.env['ir.actions.report'].sudo()

        if hasattr(model, 'company_id'):
            if len(model.company_id) > 1:
                raise UserError(_('Multi company reports are not supported.'))
            ReportAction = ReportAction.with_company(model.company_id)

        method_name = '_render_qweb_%s' % (report_type)
        report = getattr(ReportAction, method_name)(report_ref, list(model.ids), data={'report_type': report_type})[0]
        headers = self._get_http_headers(model, report_type, report, download)
        return request.make_response(report, headers=list(headers.items()))

    def _get_http_headers(self, model, report_type, report, download):
        headers = {
            'Content-Type': 'application/pdf' if report_type == 'pdf' else 'text/html',
            'Content-Length': len(report),
        }
        if report_type == 'pdf':
            filename = "%s.pdf" % (re.sub(r'\W+', '_', model._get_report_base_filename()))
            headers['Content-Disposition'] = content_disposition(filename, disposition_type='attachment' if download else 'inline')
        return headers

def get_error(e, path=''):
    """ Recursively dereferences `path` (a period-separated sequence of dict
    keys) in `e` (an error dict or value), returns the final resolution IIF it's
    an str, otherwise returns None
    """
    for k in (path.split('.') if path else []):
        if not isinstance(e, dict):
            return None
        e = e.get(k)

    return e if isinstance(e, str) else None
