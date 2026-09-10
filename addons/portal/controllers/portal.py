# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
import re

from werkzeug import urls

from odoo import SUPERUSER_ID, _, http
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    MissingError,
    UserError,
)
from odoo.http import request, route
from odoo.http.session import logout
from odoo.http.stream import content_disposition
from odoo.tools import consteq
from odoo.tools.translate import LazyTranslate

from odoo.addons.portal.controllers.address import Address

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


class CustomerPortal(Address):

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

        PortalEntry = request.env['portal.entry']
        portal_entries = dict(
            PortalEntry._read_group(
                [('show_in_portal', '=', True)],
                groupby=["category"],
                aggregates=['id:recordset']
            )
        )
        portal_cards = PortalEntry.concat(
            entries for category, entries in portal_entries.items() if category != 'alert'
        ).sorted()
        portal_hidden_cards = PortalEntry.search([
            ('category', '!=', 'alert'),
            ('show_in_portal', '=', False),
        ])
        return {
            'sales_user': sales_user_sudo,
            'page_name': 'home',
            'portal_entries': portal_entries,
            'portal_cards': portal_cards,
            'portal_hidden_cards': portal_hidden_cards,
        }

    def _prepare_portal_counter_values(self, counter):
        """ Return the values needed to compute the record count of the given badge counter in portal.

        Override to return a tuple with:
        - the model name on which to execute the search_count,
        - the record domain,
        - the access level required as a string, or 'sudo'
        """
        return False, False, False

    @route(['/my/counters'], type='jsonrpc', auth="user", website=True, readonly=True)
    def counters(self, counters, **kw):
        """Compute each badges record count for /my & /my/home routes template rendering.

        :param dict counters: Dictionary mapping the displayed badges to their entry category.
        :return dict: Dictionary mapping the displayed badges to their record count.
        """
        res = {}
        for counter, category in counters.items():
            model_name, domain, access = self._prepare_portal_counter_values(counter)
            count = 0
            if model_name:
                Model = request.env[model_name].sudo(request.env.su or access == 'sudo')
                if access == 'sudo' or not isinstance(access, str) or Model.has_access(access):
                    # Need precise count for alerts and discuss unread messages, else
                    # only need to know if there's one matching record or not to display the card.
                    precise_count = counter == 'discuss_count' or category == "alert"
                    count = Model.search_count(domain, limit=None if precise_count else 1)
            res[counter] = count
        # For performance, cache counters as boolean to prevent recomputing the card visibility on each refresh.
        cache = request.session.get('portal_counters', {}).copy()
        cache.update({k: bool(v) for k, v in res.items() if k.endswith('_count')})
        if cache != request.session.get('portal_counters'):
            request.session['portal_counters'] = cache
        return res

    @route(['/my', '/my/home'], type='http', auth="user", website=True, list_as_website_content=_lt("User Dashboard"))
    def home(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update(self.counters({}))
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
            **self._prepare_portal_layout_values(),
            **self._prepare_address_form_values(
                partner_sudo=request.env.user.partner_id,
                # Main address should always have delivery & billing information set
                use_delivery_as_billing=True,
                callback=redirect,
            ),
            'page_name': 'my_details',
        }

    # Security

    @route('/my/security', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def security(self, **post):
        values = self._prepare_portal_layout_values()
        values['get_error'] = get_error
        values['allow_api_keys'] = request.env['ir.config_parameter'].sudo().get_bool('portal.allow_api_keys')
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
                logout(request.session)
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
