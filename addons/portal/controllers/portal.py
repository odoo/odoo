# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
import re

from werkzeug import urls
from werkzeug.exceptions import Forbidden

from odoo import http, tools, _, SUPERUSER_ID, _lt
from odoo.exceptions import AccessDenied, AccessError, MissingError, UserError, ValidationError
from odoo.http import content_disposition, Controller, request, route
from odoo.tools import consteq

# --------------------------------------------------
# Misc tools
# --------------------------------------------------

def pager(url, total, page=1, step=30, scope=5, url_args=None):
    """ Generate a dict with required value to render `website.pager` template.

    This method computes url, page range to display, ... in the pager.

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
    scope -= 1

    pmin = max(page - int(math.floor(scope/2)), 1)
    pmax = min(pmin + scope, page_count)

    if pmax - pmin < scope:
        pmin = pmax - scope if pmax - scope > 0 else 1

    def get_url(page):
        _url = "%s/page/%s" % (url, page) if page > 1 else url
        if url_args:
            _url = "%s?%s" % (_url, urls.url_encode(url_args))
        return _url

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
        "page_start": {
            'url': get_url(pmin),
            'num': pmin
        },
        "page_previous": {
            'url': get_url(max(pmin, page - 1)),
            'num': max(pmin, page - 1)
        },
        "page_next": {
            'url': get_url(min(pmax, page + 1)),
            'num': min(pmax, page + 1)
        },
        "page_end": {
            'url': get_url(pmax),
            'num': pmax
        },
        "page_last": {
            'url': get_url(page_count),
            'num': page_count
        },
        "pages": [
            {'url': get_url(page_num), 'num': page_num} for page_num in range(pmin, pmax+1)
        ]
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

    @route(['/my/counters'], type='json', auth="user", website=True)
    def counters(self, counters, **kw):
        cache = (request.session.portal_counters or {}).copy()
        res = self._prepare_home_portal_values(counters)
        cache.update({k: bool(v) for k, v in res.items() if k.endswith('_count')})
        if cache != request.session.portal_counters:
            request.session.portal_counters = cache
        return res

    @route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update(self._prepare_home_portal_values([]))
        return request.render("portal.portal_my_home", values)

    @route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values.update({
            'error': {},
            'error_message': [],
        })

        if post and request.httprequest.method == 'POST':
            if not partner.can_edit_vat():
                post['country_id'] = str(partner.country_id.id)

            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                values = {key: post[key] for key in self._get_mandatory_fields()}
                values.update({key: post[key] for key in self._get_optional_fields() if key in post})
                for field in set(['country_id', 'state_id']) & set(values.keys()):
                    try:
                        values[field] = int(values[field])
                    except:
                        values[field] = False
                values.update({'zip': values.pop('zipcode', '')})
                self.on_account_update(values, partner)
                partner.sudo().write(values)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my/home')

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])

        values.update({
            'partner_sudo': partner,
            'countries': countries,
            'states': states,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'partner_can_edit_vat': partner.can_edit_vat(),
            'redirect': redirect,
            'page_name': 'my_details',
        })

        response = request.render("portal.portal_my_details", values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    def on_account_update(self, values, partner):
        pass

    @route(['/my/addresses'], type='http', auth='user', website=True)
    def addresses(self, **kwargs):
        values = {
            **self._prepare_portal_layout_values(),
            'partner': request.env.user.partner_id,
            'page_name': 'my_addresses'
        }
        # test default
        if request.env.user.partner_id:
            if not request.env.user.partner_id.is_default_billing_address and not any(child.is_default_billing_address for child in request.env.user.partner_id.child_ids):
                request.env.user.partner_id.is_default_billing_address = True

            if not request.env.user.partner_id.is_default_shipping_address and not any(child.is_default_shipping_address for child in request.env.user.partner_id.child_ids):
                request.env.user.partner_id.is_default_shipping_address = True
        return request.render("portal.portal_my_addresses", values)

    @route('/portal/address', type='http', methods=['GET'], auth='public', website=True, sitemap=False)
    def portal_address(self,
                       partner_id=None,
                       address_type='invoice',
                       template_to_render='portal.portal_my_details',
                       **query_params
                    ):
        """ Display the checkout page.

        :param dict query_params: The additional query string parameters.
        :return: The rendered checkout page.
        :rtype: str
        """
        partner_id = partner_id and int(partner_id)

        # Retrieve the partner whose address to update, if any, and its address type.
        partner_sudo, address_type = self._prepare_address_update(
            partner_id=partner_id, address_type=address_type, **query_params
        )

        # Render the address form.
        address_form_values = self._prepare_address_form_values(
            partner_sudo,
            address_type=address_type,
            **query_params
        )
        return request.render(template_to_render, address_form_values)

    @route('/address/update_address', type='json', auth='public', website=True)
    def portal_update_address(self, partner_id, address_type='billing', **kw):
        partner_id = int(partner_id)
        ResPartner = request.env['res.partner'].sudo()
        partner_sudo = ResPartner.browse(partner_id).exists()
        if not partner_sudo._can_be_edited_by_current_customer(address_type):
            raise Forbidden()

        partner_sudo._update_delivery_and_shipping_address(partner_id, address_type, **kw)

    @route(['/archive/address/<int:partner_id>'], type='http', auth="user")
    def address_archive(self, partner_id):
        """ Archive an address associated with the logged-in user.

        This method deactivates the address if it belongs to the current user or one of their
        child addresses.If the address is associated with an active user, the request is
        redirected with an error.

        :param int partner_id: The ID of the partner address to archive.
        :raises Forbidden: If the address does not belong to the logged-in user or their child addresses.
        :return: A redirect to the addresses page.
        """
        partner = request.env['res.partner'].browse(partner_id)
        address_type = partner.type
        if not partner._can_be_edited_by_current_customer(address_type):
            raise Forbidden()

        if partner.user_ids.filtered(lambda user: user.active):
            return request.redirect('/my/addresses?error=True')
        else:
            partner.sudo().write({'active': False})
        return request.redirect('/my/addresses')

    def _prepare_address_update(self, partner_id=None, address_type=None, **kwargs):
        """ Find the partner whose address to update and return it along with its address type.

        :param int partner_id: The partner whose address to update, if any, as a `res.partner` id.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :return: The partner whose address to update, if any, and its address type.
        :rtype: tuple[res.partner, str]
        :raise Forbidden: If the customer is not allowed to update the given address.
        """
        PartnerSudo = request.env['res.partner'].with_context(show_address=1).sudo()
        partner_sudo = PartnerSudo.browse(partner_id)

        if partner_sudo and not partner_sudo._can_be_edited_by_current_customer(
                address_type=address_type, **kwargs
            ):
            raise Forbidden()

        return partner_sudo, address_type

    def _prepare_address_form_values(
        self, partner_sudo, address_type, use_same=None, callback='', **_kwargs
    ):
        """ Prepare and return the values to use to render the address form.

        :param partner_sudo: The partner whose address to update through the address form.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param str callback:
        :return: The checkout page values.
        :rtype: dict
        """
        can_edit_vat = (
            address_type in ['invoice', 'billing']
            and (not partner_sudo or partner_sudo.can_edit_vat())
        )

        ResCountrySudo = request.env['res.country'].sudo()
        country_sudo = partner_sudo.country_id
        if not country_sudo:
            country_sudo = request.env.user.country_id

        state_id = partner_sudo.state_id.id
        address_fields = country_sudo and country_sudo.get_address_fields() or ['city', 'zip']

        return {
            'partner_sudo': partner_sudo,  # If set, customer is editing an existing address
            'partner_id': partner_sudo.id,
            'address_type': address_type,  # 'billing' or 'delivery'
            'type': address_type,
            'can_edit_vat': can_edit_vat,
            'callback': callback,
            'use_same': use_same,
            'discard_url': '/my/addresses',
            'country': country_sudo,
            'countries': ResCountrySudo.search([]),
            'has_invoice': partner_sudo.can_edit_info() if partner_sudo else True,
            'state_id': state_id or 1,
            'country_states': country_sudo.state_ids,
            'zip_before_city': (
                'zip' in address_fields
                and address_fields.index('zip') < address_fields.index('city')
            ),
            'show_vat': bool(address_type in ['contact', 'billing', 'invoice'] and not partner_sudo.parent_id),
            'vat_label': _lt("VAT"),
        }

    @route(
        '/portal/address/submit', type='http', methods=['POST'], auth='public', website=True,
        sitemap=False
    )
    def portal_address_submit(
            self,
            partner_id=None,
            address_type='billing',
            use_same=None,
            required_fields=None,
            **form_data
        ):
        """ Create or update an address.

        If it succeeds, it returns the URL to redirect (client-side) to. If it fails (missing or
        invalid information), it highlights the problematic form input with the appropriate error
        message.

        :param str partner_id: The partner whose address to update with the address form, if any.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param str use_same: Whether the provided address should be used as both the billing and the
                             delivery address. 'true' or 'false'.
        :param str required_fields: The additional required address values, as a comma-separated
                                    list of `res.partner` fields.
        :param dict form_data: The form data to process as address values.
        :return: A JSON-encoded feedback, with either the success URL or an error message.
        :rtype: str
        """
        partner_sudo, address_type = self._prepare_address_update(
            partner_id=partner_id and int(partner_id), address_type=address_type
        )

        required_fields = required_fields or ''

        # Parse form data into address values, and extract incompatible data as extra form data.
        address_values, extra_form_data = self._parse_portal_form_data(form_data)
        if 'country_id' not in address_values and partner_sudo.country_id:
            address_values['country_id'] = partner_sudo.country_id.id
        if 'state_id' not in address_values and partner_sudo.state_id:
            address_values['state_id'] = partner_sudo.state_id.id

        # Validate the address values and highlights the problems in the form, if any.
        invalid_fields, missing_fields, error_messages = self._validate_portal_address_values(
            address_values, partner_sudo, address_type, use_same, required_fields, **extra_form_data
        )

        if error_messages:
            return json.dumps({
                'invalid_fields': list(invalid_fields | missing_fields),
                'messages': error_messages,
            })
        if not partner_sudo:  # Creation of a new address.
            address_values['parent_id'] = request.env.user.partner_id.id
            create_context = tools.clean_context(request.env.context)
            create_context.update({
                'tracking_disable': True,
                'no_vat_validation': True,
            })
            partner_sudo = request.env['res.partner'].sudo().with_context(
                create_context
            ).create(address_values)
        else:
            partner_sudo.write(address_values)

        return json.dumps({
            'successUrl': 'my/addresses',
        })

    def _parse_portal_form_data(self, form_data):
        """ Parse the form data and return them converted into address values and extra form data.

        :param dict form_data: The form data to convert to address values.
        :return: A tuple of converted address values and extra form data.
        :rtype: tuple[dict, dict]
        """
        address_values = {}
        extra_form_data = {}

        ResPartner = request.env['res.partner']
        partner_fields = ResPartner._fields
        for key, value in form_data.items():
            if isinstance(value, str):
                value = value.strip()
            if key in partner_fields:
                field = partner_fields[key]
                if field.type == 'many2one' and isinstance(value, str) and value.isdigit():
                    address_values[key] = field.convert_to_cache(int(value), ResPartner)
                else:
                    # Always keep field values, even if falsy, as it might be for resetting a field.
                    address_values[key] = field.convert_to_cache(value, ResPartner)
            elif value:  # The value cannot be saved on the `res.partner` model.
                extra_form_data[key] = value

        if (
            hasattr(ResPartner, 'check_vat')  # The `base_vat` module is installed.
            and address_values.get('vat')
            and address_values.get('country_id')
        ):
            address_values['vat'] = ResPartner.fix_eu_vat_number(
                address_values['country_id'],
                address_values['vat'],
            )

        return address_values, extra_form_data

    def _get_writable_fields(self):
        # Need to override it in ecommerce
        return {}

    def _validate_portal_address_values(
        self, address_values, partner_sudo, address_type, use_same, required_fields, **_kwargs
    ):
        """ Validate the address values and return the invalid fields, the missing fields, and any
        error messages.
        :param dict address_values: The address values to validates.
        :param res.partner partner_sudo: The partner whose address values to validate, if any (can
                                         be empty).
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param bool use_same: Whether the provided address should be used as both the billing and
                              the delivery address.
        :param str required_fields: The additional required address values, as a comma-separated
                                    list of `res.partner` fields.
        :param dict _kwargs: Locally unused parameters including the extra form data.
        :return: The invalid fields, the missing fields, and any error messages.
        :rtype: tuple[set, set, list]
        """
        # data: values after preprocess
        invalid_fields = set()
        missing_fields = set()
        error_messages = []

        if partner_sudo:
            # Prevent changing the VAT number if invoices have been issued.
            if (
                'vat' in address_values
                and address_values['vat'] != partner_sudo.vat
                and not partner_sudo.can_edit_vat()
            ):
                invalid_fields.add('vat')
                error_messages.append(_(
                    "Changing VAT number is not allowed once document(s) have been issued for your"
                    " account. Please contact us directly for this operation."
                ))

        # Validate the email.
        if address_values.get('email') and not tools.single_email_re.match(address_values['email']):
            invalid_fields.add('email')
            error_messages.append(_("Invalid Email! Please enter a valid email address."))

        # Validate the VAT number.
        ResPartnerSudo = request.env['res.partner'].sudo()
        if (
            address_values.get('vat') and hasattr(ResPartnerSudo, 'check_vat')
            and 'vat' not in invalid_fields
        ):
            partner_dummy = ResPartnerSudo.new({
                fname: address_values[fname]
                for fname in self._get_vat_validation_fields()
                if fname in address_values
            })
            try:
                partner_dummy.check_vat()
            except ValidationError as exception:
                invalid_fields.add('vat')
                error_messages.append(exception.args[0])

        # Build the set of required fields from the address form's requirements.
        required_field_set = {f for f in required_fields.split(',') if f}

        # Complete the set of required fields based on the address type.
        country_id = address_values.get('country_id')
        country = request.env['res.country'].browse(country_id)
        if address_type == 'delivery':
            required_field_set |= self._get_mandatory_delivery_address_fields(country)
        if address_type == 'invoice':
            required_field_set |= self._get_mandatory_billing_address_fields(country)

        # Verify that no required field has been left empty.
        for field_name in required_field_set:
            if not address_values.get(field_name):
                missing_fields.add(field_name)
        if missing_fields:
            error_messages.append(_("Some required fields are empty."))

        return invalid_fields, missing_fields, error_messages

    def _get_vat_validation_fields(self):
        return {'country_id', 'vat'}

    def _check_delivery_address(self, partner_sudo):
        """ Check that all mandatory delivery fields are filled for the given partner.

        :param res.partner: The partner whose delivery address to check.
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
        return self._get_mandatory_address_fields(country_sudo)

    def _get_mandatory_billing_address_fields(self, country_sudo):
        """ Return the set of mandatory billing field names.

        :param res.country country_sudo: The country to use to build the set of mandatory fields.
        :return: The set of mandatory billing field names.
        :rtype: set
        """
        field_names = self._get_mandatory_address_fields(country_sudo)
        # Include the required billing fields from the portal logic.
        field_names |= set(self._get_mandatory_fields())
        return field_names

    def _get_mandatory_address_fields(self, country_sudo):
        """ Return the set of common mandatory address fields.

        :param res.country country_sudo: The country to use to build the set of mandatory fields.
        :return: The set of common mandatory address field names.
        :rtype: set
        """
        field_names = {'name', 'street', 'city', 'country_id', 'phone'}
        if country_sudo.state_required:
            field_names.add('state_id')
        if country_sudo.zip_required:
            field_names.add('zip')
        return field_names

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

    @http.route('/portal/attachment/remove', type='json', auth='public')
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

    @route(['/portal/country_info/<model("res.country"):country>'], type='json', auth="public", methods=['POST'], website=True)
    def portal_country_info(self, country, address_type, **kw):
        address_fields = country.get_address_fields()
        if address_type in ['invoice', 'billing']:
            required_fields = self._get_mandatory_billing_address_fields(country)
        else:
            required_fields = self._get_mandatory_delivery_address_fields(country)
        return {
            'fields': address_fields,
            'zip_before_city': address_fields.index('zip') < address_fields.index('city'),
            'states': [(st.id, st.name, st.code) for st in country.sudo().state_ids],
            'phone_code': country.phone_code,
            'required_fields': list(required_fields),
        }

    def details_form_validate(self, data, partner_creation=False):
        error = dict()
        error_message = []

        # Validation
        for field_name in self._get_mandatory_fields():
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email address.'))

        # vat validation
        partner = request.env.user.partner_id
        if data.get("vat") and partner and partner.vat != data.get("vat"):
            # Check the VAT if it is the public user too.
            if partner_creation or partner.can_edit_vat():
                if hasattr(partner, "check_vat"):
                    if data.get("country_id"):
                        data["vat"] = request.env["res.partner"].fix_eu_vat_number(int(data.get("country_id")), data.get("vat"))
                    partner_dummy = partner.new({
                        'vat': data['vat'],
                        'country_id': (int(data['country_id'])
                                       if data.get('country_id') else False),
                    })
                    try:
                        partner_dummy.check_vat()
                    except ValidationError as e:
                        error["vat"] = 'error'
                        error_message.append(e.args[0])
            else:
                error_message.append(_('Changing VAT number is not allowed once document(s) have been issued for your account. Please contact us directly for this operation.'))

        # error message for empty required fields
        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        unknown = [k for k in data if k not in self._get_mandatory_fields() + self._get_optional_fields()]
        if unknown:
            error['common'] = 'Unknown field'
            error_message.append("Unknown field '%s'" % ','.join(unknown))

        return error, error_message

    def _get_mandatory_fields(self):
        """ This method is there so that we can override the mandatory fields """
        return ["name", "phone", "email", "street", "city", "country_id"]

    def _get_optional_fields(self):
        """ This method is there so that we can override the optional fields """
        return ["street2", "zipcode", "state_id", "vat", "company_name"]

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
        if report_type == 'pdf' and download:
            filename = "%s.pdf" % (re.sub(r'\W+', '_', model._get_report_base_filename()))
            headers['Content-Disposition'] = content_disposition(filename)
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
