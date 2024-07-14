# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from operator import itemgetter
from collections import OrderedDict

from markupsafe import Markup

from odoo import http, _
from odoo.exceptions import MissingError
from odoo.http import request
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager, get_records_pager

from odoo.tools import groupby as groupbyelem
from odoo.osv.expression import AND


class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super(CustomerPortal, self)._prepare_home_portal_values(counters)
        if 'to_sign_count' in counters:
            partner_id = request.env.user.partner_id
            values['to_sign_count'] = request.env['sign.request.item'].sudo().search_count([
                ('partner_id', '=', partner_id.id), ('sign_request_id.state', '=', 'sent')
            ])
        if 'sign_count' in counters:
            partner_id = request.env.user.partner_id
            values['sign_count'] = request.env['sign.request.item'].sudo().search_count([
                ('partner_id', '=', partner_id.id), '|', ('sign_request_id.state', '=', 'refused'), '|', ('state', '=', 'completed'), ('is_mail_sent', '=', True)
            ])
        return values

    @http.route(['/my/signatures', '/my/signatures/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_signatures(self, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='all',
                             groupby='none', filterby=None, **kw):

        values = self._prepare_portal_layout_values()
        partner_id = request.env.user.partner_id
        SignRequestItem = request.env['sign.request.item'].sudo()
        default_domain = [('partner_id', '=', partner_id.id), '|', ('sign_request_id.state', '=', 'refused'), '|', ('state', '=', 'completed'), ('is_mail_sent', '=', True)]

        searchbar_sortings = {
            'new': {'label': _('Newest'), 'order': 'sign_request_id desc'},
            'date': {'label': _('Signing Date'), 'order': 'signing_date desc'},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': default_domain},
            'tosign': {'label': _('To sign'), 'domain': AND([default_domain, [('state', '=', 'sent'),
                                                                              ('sign_request_id.state', '=', 'sent')]])},
            'completed': {'label': _('Completed'), 'domain': AND([default_domain, [('state', '=', 'completed')]])},
            'signed': {'label': _('Fully Signed'),
                       'domain': AND([default_domain, [('sign_request_id.state', '=', 'signed')]])},
        }

        searchbar_inputs = {
            'all': {'input': 'all', 'label': Markup(_('Search <span class="nolabel"> (in Document)</span>'))},
        }

        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'state': {'input': 'state', 'label': _('Status')},
        }

        # default sortby order
        if not sortby:
            sortby = 'new'
        sort_order = searchbar_sortings[sortby]['order']
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain = searchbar_filters[filterby]['domain']
        if date_begin and date_end:
            domain = AND([domain, [('signing_date', '>', date_begin), ('signing_date', '<=', date_end)]])
        # search only the document name
        if search and search_in:
            domain = AND([domain, [('reference', 'ilike', search)]])
        pager = portal_pager(
            url='/my/signatures',
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby,
                      'search_in': search_in, 'search': search},
            total=SignRequestItem.search_count(domain),
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        if groupby == 'state':
            sort_order = 'state, %s' % sort_order

        # search the count to display, according to the pager data
        sign_requests_items = SignRequestItem.search(domain, order=sort_order, limit=self._items_per_page,
                                                     offset=pager['offset'])
        request.session['my_signatures_history'] = sign_requests_items.ids[:100]
        if groupby == 'state':
            grouped_signatures = [SignRequestItem.concat(*g)
                                  for k, g in groupbyelem(sign_requests_items, itemgetter('state'))]
        else:
            grouped_signatures = [sign_requests_items]

        values.update({
            'date': date_begin,
            'grouped_signatures': grouped_signatures,
            'page_name': 'signatures',
            'pager': pager,
            'default_url': '/my/signatures',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'searchbar_groupby': searchbar_groupby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'groupby': groupby,
            'sortby': sortby,
            'filterby': filterby,
        })
        return request.render('sign.sign_portal_my_requests', values)

    @http.route(['/my/signature/<int:item_id>'], type='http', auth='user', website=True)
    def portal_my_signature(self, item_id, **kwargs):
        partner_id = request.env.user.partner_id
        sign_item_sudo = request.env['sign.request.item'].sudo().browse(item_id)
        if not sign_item_sudo.exists()\
                or sign_item_sudo.partner_id != partner_id \
                or sign_item_sudo.sign_request_id.state == 'canceled' \
                or (sign_item_sudo.state == 'sent' and sign_item_sudo.is_mail_sent is False):
            return request.redirect('/my/')
        url = f'/sign/document/{sign_item_sudo.sign_request_id.id}/{sign_item_sudo.access_token}?portal=1'
        values = {
            'page_name': 'signature',
            'my_sign_item': sign_item_sudo,
            'url': url
        }
        # exclude access_token from kwargs to prevent redundant passing
        kwargs.pop('access_token', None)
        values = self._get_page_view_values(sign_item_sudo, sign_item_sudo.access_token, values,
                                            'my_signatures_history', False, **kwargs)
        return request.render('sign.sign_portal_my_request', values)
