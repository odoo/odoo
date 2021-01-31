# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.osv.expression import OR


class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values['order_count'] = request.env['nursery.order'].search_count([])
        if values.get('sales_user', False):
            values['title'] = _("Salesperson")
        return values

    def _order_get_page_view_values(self, order, access_token, **kwargs):
        values = {
            'page_name': 'order',
            'order': order,
        }
        return self._get_page_view_values(order, access_token, values, 'my_orders_history', False, **kwargs)

    @http.route(['/my/order', '/my/order/page/<int:page>'], type='http', auth="user", website=True)
    def my_nursery_orders(self, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        domain = []

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Subject'), 'order': 'name'},
        }
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Default Group By 'create_date'
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, [
                    '|', '|',
                    ('name', 'ilike', search),
                    ('line_ids.plant_id.description', 'ilike', search),
                    ('line_ids.plant_id.description_short', 'ilike', search)]])
            if search_in in ('customer', 'all'):
                search_domain = OR([search_domain, [('customer_id', 'ilike', search)]])
            if search_in in ('message', 'all'):
                search_domain = OR([search_domain, [('message_ids.body', 'ilike', search)]])
            domain += search_domain

        # pager
        order_count = request.env['nursery.order'].search_count(domain)
        pager = portal_pager(
            url="/my/order",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=order_count,
            page=page,
            step=self._items_per_page
        )

        orders = request.env['nursery.order'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_orders_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders,
            'page_name': 'order',
            'default_url': '/my/order',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'sortby': sortby,
            'search_in': search_in,
            'search': search,
        })
        return request.render("plant_nursery.portal_nursery_order", values)

    @http.route([
        "/nursery/order/<int:order_id>",
        "/nursery/order/<int:order_id>/<token>",
        '/my/order/<int:order_id>'
    ], type='http', auth="public", website=True)
    def orders_followup(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('nursery.order', order_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._order_get_page_view_values(order_sudo, access_token, **kw)
        return request.render("plant_nursery.orders_followup", values)
