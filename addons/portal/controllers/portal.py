# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import functools
import json
import logging
import math
import re

from itertools import chain
from werkzeug import urls

from odoo import fields as odoo_fields, http, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, AccessError, MissingError, UserError, AccessDenied
from odoo.http import content_disposition, Controller, request, route
from odoo.tools import consteq

# --------------------------------------------------
# Misc tools
# --------------------------------------------------

_logger = logging.getLogger(__name__)
def pager(url, total, page=1, step=30, scope=5, url_args=None):
    """ Generate a dict with required value to render `website.pager` template. This method compute
        url, page range to display, ... in the pager.
        :param url : base url of the page link
        :param total : number total of item to be splitted into pages
        :param page : current page
        :param step : item per page
        :param scope : number of page to display on pager
        :param url_args : additionnal parameters to add as query params to page url
        :type url_args : dict
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
        return {
            'prev_record': idx != 0 and getattr(current.browse(ids[idx - 1]), attr_name),
            'next_record': idx < len(ids) - 1 and getattr(current.browse(ids[idx + 1]), attr_name),
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

    """format of the following dicts : key = model_field_name : value = view_field_name
    we use this format because the address form will contain fields from various models
    (i.e. bank informations) and view variable names can not always be identical to field names
    """
    # names fields for res.partner
    MANDATORY_PARTNER_FIELDS = {
        "name": "name",
        "phone": "phone",
        "email": "email",
        "street": "street",
        "city": "city",
        "country_id": "country_id",
        "type": "type",
    }
    OPTIONAL_PARTNER_FIELDS = {
        "zip": "zipcode",
        "state_id": "state_id",
        "vat": "vat",
        "company_name": "company_name",
    }

    _items_per_page = 80

    def _prepare_portal_layout_values(self):
        """Values for /my/* templates rendering.

        Does not include the record counts.
        """
        # get customer sales rep
        sales_user = False
        partner = request.env.user.partner_id
        if partner.user_id and not partner.user_id._is_public():
            sales_user = partner.user_id

        return {
            'sales_user': sales_user,
            'page_name': 'home',
        }

    def _prepare_portal_counters_values(self, counters):
        """Values for /my & /my/home routes template rendering.

        Includes the record count for the displayed menu elements.
        where 'counters' is the list of the displayed counters in the menu
        elements and so the list to compute.
        """
        return {}

    def _prepare_portal_overview_values(self):
        """Values for /my & /my/home routes template rendering.

        Includes the desired counters (optional) and descriptions (mandatory
        for each description_data) for the displayed menu elements
        Expected values format:
        {
            'description_data_name': [{
                'description': 'translated description',
                'counter': 'counter_name',  # name sent to /my/counters
            }, ...], ...
        }
        """
        return {
            'my_account_description': [{
                'description': _("Addresses, Payments, Security, Users"),
            }]
        }

    def _is_own_partner_address(self, partner, address_id):
        """Checks whether address_id is the id of a res.partner representing:
            - the main address of partner (partner.id)
            - an invoice address from partner.child_ids
            - a delivery address from partner.child_ids
        """
        # if address_id is partner's main address
        if partner.id == address_id:
            return True
        # if address_id partner's secondary address
        return address_id in partner.child_ids.filtered(lambda partner: partner.type in ['invoice', 'delivery']).ids

    def _render_portal_my_address(self, values):
        response = request.render("portal.portal_my_address", values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    def _prepare_address_form_values(self, address_id=None):
        values = self._prepare_portal_layout_values()

        partner = request.env.user.partner_id
        address = request.env['res.partner'].with_context(show_address=1).browse(address_id) if address_id else False

        if address:
            fields = {**self.MANDATORY_PARTNER_FIELDS, **self.OPTIONAL_PARTNER_FIELDS}
            # add address data
            values.update({value: getattr(address, key) for key, value in fields.items()})

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])

        values.update({
            'partner': partner,
            'address': address,
            'countries': countries,
            'states': states,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'page_name': 'my_details',
        })
        return values

    @route(['/my/address/create', '/my/address/<int:address_id>/update'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def address_write(self, address_id=None, redirect=None, **post):
        partner = request.env.user.partner_id
        if address_id is not None and not self._is_own_partner_address(partner, address_id):
            return request.redirect(redirect or '/my/account')

        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        address = Partner.browse(address_id) if address_id else False
        is_main_address = address and address.id == partner.id
        fields = {**self.MANDATORY_PARTNER_FIELDS, **self.OPTIONAL_PARTNER_FIELDS}

        data = {key: post.get(value, False) for key, value in fields.items()}
        error, error_message = self.details_form_validate(data, validate_main_address=is_main_address)
        if not error:
            if address:
                self.on_account_update(data, partner)
                address.write(data)
            else:
                data['parent_id'] = partner.id
                address = Partner.create(data)
            return request.redirect(redirect or '/my/account')

        values = {
            **self._prepare_address_form_values(address_id),
            'error': error,
            'error_message': error_message,
            'redirect': redirect,
        }
        return self._render_portal_my_address(values)

    @route(['/my/address/<int:address_id>/delete'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def address_delete(self, address_id, redirect=None, **kw):
        partner = request.env.user.partner_id
        if not self._is_own_partner_address(partner, address_id) or address_id == partner.id:
            return request.redirect(redirect or '/my/account')

        address_sudo = request.env['res.partner'].browse(address_id).sudo()
        address_sudo.unlink()

        return request.redirect(redirect or '/my/account')

    @route(['/my/address', '/my/address/<int:address_id>'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def address_read(self, address_id=None, redirect=None, **kw):
        partner = request.env.user.partner_id
        if address_id is not None and not self._is_own_partner_address(partner, address_id):
            return request.redirect(redirect or '/my/account')

        values = {
            **self._prepare_address_form_values(address_id),
            'redirect': redirect
        }
        return self._render_portal_my_address(values)

    @route(['/my/counters'], type='json', auth="user", website=True)
    def counters(self, counters, **kw):
        return self._prepare_portal_counters_values(counters)

    @route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update(self._prepare_portal_overview_values())
        values['company'] = request.env.company
        return request.render("portal.portal_my_home", values)

    @route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        values = self._prepare_portal_layout_values()

        partner = request.env.user.partner_id

        values.update({
            'page_name': 'my_details',
            'partner': partner,
            'invoice_addresses': partner.child_ids.filtered(lambda address: address.type == 'invoice'),
            'delivery_addresses': partner.child_ids.filtered(lambda address: address.type == 'delivery'),
        })
        return request.render("portal.portal_my_details", values)

    def on_account_update(self, values, partner):
        pass

    def _get_commercial_partners_and_users(self):
        partner = request.env.user.partner_id
        commercial_partners = partner.commercial_partner_id.child_ids
        portal_users = commercial_partners.filtered(lambda partner: partner.user_ids and partner.user_ids[0].has_group('base.group_portal')) \
                                          .mapped(lambda partner: partner.user_ids[0] if partner.user_ids else partner.user_ids)
        return commercial_partners, portal_users

    def _prepare_users_accesses_values(self):
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'users_accesses',
            'get_message': get_message,
        })
        return values

    @route('/my/users_accesses', type='http', auth='user', website=True, methods=['POST'])
    def users_accesses_invitation(self, portal_user_id=None, user_email=None, **kw):
        portal_user_id = int(portal_user_id) if isinstance(portal_user_id, str) and portal_user_id.isdecimal() else None
        user_email = user_email.strip() if isinstance(user_email, str) else None

        values = self._prepare_users_accesses_values()
        commercial_partners, portal_users = self._get_commercial_partners_and_users()

        success_message = {'success': _("Invitation sent")}
        if portal_user_id:
            if portal_user_id in portal_users.ids:
                invited_partner = portal_users.browse(portal_user_id).partner_id
                try:
                    invited_partner.action_resend_portal_access_invitation()
                    values['success'] = success_message
                except UserError as e:
                    values['errors'] = {'error': str(e)}
            else:
                values['errors'] = {'error': _("The partner does not exists or you do not have the rights to reinvite them, please ask an administrator to do it for you.")}
        elif user_email:
            invited_partner = commercial_partners.filtered(lambda partner: partner.email == user_email)
            if invited_partner:
                try:
                    invited_partner.action_grant_portal_access()
                    values['success'] = success_message
                    portal_users += invited_partner.user_ids[0]
                except UserError as e:
                    values['errors'] = {'error': str(e)}
            else:
                values['errors'] = {'error': _('No registered partner with the email "%(email)s" in your company, please ask an administrator to register it first.',
                                               email=user_email)}
        values['portal_users'] = portal_users.sorted(lambda user: user.name)
        return request.render("portal.portal_my_users_accesses", values)

    @route('/my/users_accesses', type='http', auth='user', website=True, methods=['GET'])
    def users_accesses(self, **kw):
        values = self._prepare_users_accesses_values()
        values['portal_users'] = self._get_commercial_partners_and_users()[1].sorted(lambda user: user.name)
        return request.render("portal.portal_my_users_accesses", values)

    @route('/my/security', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def security(self, **post):
        values = self._prepare_portal_layout_values()
        values['get_message'] = get_message
        values['page_name'] = 'security'

        if request.httprequest.method == 'POST':
            values.update(self._update_password(
                post['old'].strip(),
                post['new1'].strip(),
                post['new2'].strip()
            ))

        return request.render('portal.portal_my_security', values, headers={
            'X-Frame-Options': 'DENY'
        })

    def _update_password(self, old, new1, new2):
        for k, v in [('old', old), ('new1', new1), ('new2', new2)]:
            if not v:
                return {'errors': {'password': {k: _("You cannot leave any password empty.")}}}

        if new1 != new2:
            return {'errors': {'password': {'new2': _("The new password and its confirmation must be identical.")}}}

        try:
            request.env['res.users'].change_password(old, new1)
        except UserError as e:
            return {'errors': {'password': e.name}}
        except AccessDenied as e:
            msg = e.args[0]
            if msg == AccessDenied().args[0]:
                msg = _('The old password you provided is incorrect, your password was not changed.')
            return {'errors': {'password': {'old': msg}}}

        # update session token so the user does not get logged out (cache cleared by passwd change)
        new_token = request.env.user._compute_session_token(request.session.sid)
        request.session.session_token = new_token

        return {'success': {'password': True}}

    @http.route('/portal/attachment/add', type='http', auth='public', methods=['POST'], website=True)
    def attachment_add(self, name, file, res_model, res_id, access_token=None, **kwargs):
        """Process a file uploaded from the portal chatter and create the
        corresponding `ir.attachment`.

        The attachment will be created "pending" until the associated message
        is actually created, and it will be garbage collected otherwise.

        :param name: name of the file to save.
        :type name: string

        :param file: the file to save
        :type file: werkzeug.FileStorage

        :param res_model: name of the model of the original document.
            To check access rights only, it will not be saved here.
        :type res_model: string

        :param res_id: id of the original document.
            To check access rights only, it will not be saved here.
        :type res_id: int

        :param access_token: access_token of the original document.
            To check access rights only, it will not be saved here.
        :type access_token: string

        :return: attachment data {id, name, mimetype, file_size, access_token}
        :rtype: dict
        """
        try:
            self._document_check_access(res_model, int(res_id), access_token=access_token)
        except (AccessError, MissingError) as e:
            raise UserError(_("The document does not exist or you do not have the rights to access it."))

        IrAttachment = request.env['ir.attachment']
        access_token = False

        # Avoid using sudo or creating access_token when not necessary: internal
        # users can create attachments, as opposed to public and portal users.
        if not request.env.user.has_group('base.group_user'):
            IrAttachment = IrAttachment.sudo().with_context(binary_field_real_user=IrAttachment.env.user)
            access_token = IrAttachment._generate_access_token()

        # At this point the related message does not exist yet, so we assign
        # those specific res_model and res_is. They will be correctly set
        # when the message is created: see `portal_chatter_post`,
        # or garbage collected otherwise: see  `_garbage_collect_attachments`.
        attachment = IrAttachment.create({
            'name': name,
            'datas': base64.b64encode(file.read()),
            'res_model': 'mail.compose.message',
            'res_id': 0,
            'access_token': access_token,
        })
        return request.make_response(
            data=json.dumps(attachment.read(['id', 'name', 'mimetype', 'file_size', 'access_token'])[0]),
            headers=[('Content-Type', 'application/json')]
        )

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

        if attachment_sudo.env['mail.message'].search([('attachment_ids', 'in', attachment_sudo.ids)]):
            raise UserError(_("The attachment %s cannot be removed because it is linked to a message.", attachment_sudo.name))

        return attachment_sudo.unlink()

    @http.route(['/my/main_address_confirmation_warnings'], type='json', auth="user", website=True)
    def main_address_confirmation_warnings(self, data, **kw):
        return [_("Are you sure you want to edit your main address?")]

    def details_form_validate(self, data, validate_main_address=True):
        error = dict()
        error_message = []

        # Validation
        for field_name in self.MANDATORY_PARTNER_FIELDS:
            if not data.get(field_name):
                error[self.MANDATORY_PARTNER_FIELDS[field_name]] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email address.'))

        # country_id and state_id validation and formatting
        for field in set(['country_id', 'state_id']) & set(data.keys()):
            try:
                data[field] = int(data[field]) if data[field] else False
            except ValueError:
                data[field] = False
                error[field] = 'error'

        # type validation
        if not validate_main_address and data.get('type') and not data['type'] in set(['delivery', 'invoice']):
            error['type'] = 'error'

        # vat validation
        partner = request.env.user.partner_id
        if validate_main_address and data.get("vat") and partner and partner.vat != data.get("vat"):
            if partner.can_edit_vat():
                if hasattr(partner, "check_vat"):
                    if data.get("country_id"):
                        data["vat"] = request.env["res.partner"].fix_eu_vat_number(data.get("country_id"), data.get("vat"))
                    partner_dummy = partner.new({
                        'vat': data['vat'],
                        'country_id': data['country_id'],
                    })
                    try:
                        partner_dummy.check_vat()
                    except ValidationError as err:
                        error["vat"] = 'error'
                        error_message.append(err.message)
            else:
                error["vat"] = 'error'
                error_message.append(_('Changing VAT number is not allowed once document(s) have been issued for your account. Please contact us directly for this operation.'))

        # company_name validation
        if validate_main_address and partner and not partner.can_edit_vat() and data.get("company_name") != partner.company_name:
            if partner.commercial_company_name == data["company_name"]:
                data["company_name"] = partner.company_name
            else:
                error["company_name"] = 'error'
                error_message.append(_('Changing your company name is not allowed once document(s) have been issued for your account. Please contact us directly for this operation.'))

        # error message for empty required fields
        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        unknown = [k for k in data if k not in chain(self.MANDATORY_PARTNER_FIELDS.keys(), self.OPTIONAL_PARTNER_FIELDS.keys())]
        if unknown:
            error['common'] = 'Unknown field'
            error_message.append("Unknown field '%s'" % ','.join(unknown))

        return error, error_message

    def _document_check_access(self, model_name, document_id, access_token=None):
        document = request.env[model_name].browse([document_id])
        document_sudo = document.with_user(SUPERUSER_ID).exists()
        if not document_sudo:
            raise MissingError(_("This document does not exist."))
        try:
            document.check_access_rights('read')
            document.check_access_rule('read')
        except AccessError:
            if not access_token or not document_sudo.access_token or not consteq(document_sudo.access_token, access_token):
                raise
        return document_sudo

    def _get_page_view_values(self, document, access_token, values, session_history, no_breadcrumbs, **kwargs):
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

        report_sudo = request.env.ref(report_ref).with_user(SUPERUSER_ID)

        if not isinstance(report_sudo, type(request.env['ir.actions.report'])):
            raise UserError(_("%s is not the reference of a report", report_ref))

        if hasattr(model, 'company_id'):
            if len(model.company_id) > 1:
                raise UserError(_('Multi company reports are not supported.'))
            report_sudo = report_sudo.with_company(model.company_id)

        method_name = '_render_qweb_%s' % (report_type)
        report = getattr(report_sudo, method_name)(list(model.ids), data={'report_type': report_type})[0]
        reporthttpheaders = [
            ('Content-Type', 'application/pdf' if report_type == 'pdf' else 'text/html'),
            ('Content-Length', len(report)),
        ]
        if report_type == 'pdf' and download:
            filename = "%s.pdf" % (re.sub('\W+', '-', model._get_report_base_filename()))
            reporthttpheaders.append(('Content-Disposition', content_disposition(filename)))
        return request.make_response(report, headers=reporthttpheaders)

def get_message(e, path=''):
    """ Recursively dereferences `path` (a period-separated sequence of dict
    keys) in `e` (an message dict or value), returns the final resolution IIF it's
    an str, otherwise returns None
    """
    for k in (path.split('.') if path else []):
        if not isinstance(e, dict):
            return None
        e = e.get(k)

    return e if isinstance(e, str) else None
