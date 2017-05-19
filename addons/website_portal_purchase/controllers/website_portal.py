# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import pycompat
from odoo.tools.translate import _

from odoo.addons.website_portal.controllers.main import website_account, get_records_pager


class WebsitePortal(website_account):

    def _prepare_portal_layout_values(self):
        values = super(WebsitePortal, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values['purchase_count'] = request.env['purchase.order'].search_count([
            '|',
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['purchase', 'done', 'cancel'])
        ])
        return values

    @http.route(['/my/purchase', '/my/purchase/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PurchaseOrder = request.env['purchase.order']

        domain = [
            '|',
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
        ]

        archive_groups = self._get_archive_groups('purchase.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
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

        # count for pager
        purchase_count = PurchaseOrder.search_count(domain)
        # make pager
        pager = request.website.pager(
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
            'searchbar_filters': OrderedDict(sorted(pycompat.items(searchbar_filters))),
            'filterby': filterby,
            'default_url': '/my/purchase',
        })
        return request.render("website_portal_purchase.portal_my_purchase_orders", values)

    @http.route(['/my/purchase/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_purchase_order(self, order_id=None, **kw):
        order = request.env['purchase.order'].browse(order_id)
        try:
            order.check_access_rights('read')
            order.check_access_rule('read')
        except AccessError:
            return request.render("website.403")
        history = request.session.get('my_purchases_history', [])
        values = {
            'order': order.sudo(),
        }
        values.update(get_records_pager(history, order))
        return request.render("website_portal_purchase.portal_my_purchase_order", values)
