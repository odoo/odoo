# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import OrderedDict

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.osv.expression import OR
from odoo.tools import image_process
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.addons.web.controllers.main import Binary



class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values['purchase_count'] = request.env['purchase.order'].search_count([
            ('state', 'in', ['purchase', 'done', 'cancel'])
        ])
        return values

    def _purchase_order_get_page_view_values(self, order, access_token, **kwargs):
        #
        def resize_to_48(b64source):
            if not b64source:
                b64source = base64.b64encode(Binary().placeholder())
            return image_process(b64source, size=(48, 48))

        values = {
            'order': order,
            'resize_to_48': resize_to_48,
        }
        return self._get_page_view_values(order, access_token, values, 'my_purchases_history', True, **kwargs)

    @http.route(['/my/purchase', '/my/purchase/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, search=None, search_in='content', sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PurchaseOrder = request.env['purchase.order']

        domain = []

        archive_groups = self._get_archive_groups('purchase.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'vendor': {'label': _('Vendor'), 'order': 'partner_id, id'},
            'name': {'label': _('Name'), 'order': 'name, id'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'product': {'input': 'product', 'label': _('Search in Product')},
            'vendor': {'input': 'vendor', 'label': _('Search in Vendor')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('state', 'in', ['purchase', 'done', 'cancel'])]},
            'purchase': {'label': _('Purchase Order'), 'domain': [('state', '=', 'purchase')]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
            'done': {'label': _('Locked'), 'domain': [('state', '=', 'done')]},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
            if search_in in ('product', 'all'):
                search_domain = OR([search_domain, [('order_line.product_id', 'ilike', search)]])
            if search_in in ('vendor', 'all'):
                search_domain = OR([search_domain, [('partner_id', 'ilike', search)]])
            domain += search_domain

        # count for pager
        purchase_count = PurchaseOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/purchase",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=purchase_count,
            page=page,
            step=self._items_per_page
        )
        # search the purchase orders to display, according to the pager data
        orders = PurchaseOrder.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['my_purchases_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders,
            'page_name': 'purchase',
            'pager': pager,
            'archive_groups': archive_groups,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'filterby': filterby,
            'default_url': '/my/purchase',
        })
        return request.render("purchase.portal_my_purchase_orders", values)

    @http.route(['/my/purchase/<int:order_id>'], type='http', auth="public", website=True)
    def portal_my_purchase_order(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._purchase_order_get_page_view_values(order_sudo, access_token, **kw)
        return request.render("purchase.portal_my_purchase_order", values)
