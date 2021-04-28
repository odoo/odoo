# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        SaleOrder = request.env['sale.order']
        if 'loyalty_count' in counters:
            values['loyalty_count'] = SaleOrder.search_count([
                ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
                ('state', 'in', ['sent', 'sale', 'done']),
                ('website_id', '=', request.website.id),
                '|', ('won_loyalty_points', '>', 0), ('spent_loyalty_points', '>', 0),
            ]) if SaleOrder.check_access_rights('read', raise_exception=False) else 0

        return values

    # ------------------------------------------------------------
    # My Loyalty
    # ------------------------------------------------------------

    @http.route(['/my/loyalty', '/my/loyalty/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_loyalty(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sent', 'sale', 'done']),
            ('website_id', '=', request.website.id),
            '|', ('won_loyalty_points', '>', 0), ('spent_loyalty_points', '>', 0),
        ]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
            'won': {'label': _('Won Points'), 'order': 'won_loyalty_points desc'},
            'spent': {'label': _('Spent Points'), 'order': 'spent_loyalty_points desc'},
        }
        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        order_count = SaleOrder.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/loyalty",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=order_count,
            page=page,
            step=self._items_per_page,
        )
        # content according to pager
        orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_loyalty_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders.sudo(),
            'total_points': partner.loyalty_points,
            'page_name': 'loyalty',
            'pager': pager,
            'default_url': '/my/orders',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("website_sale_loyalty.portal_my_loyalty", values)

    @http.route(['/my/loyalty/<int:order_id>'], type='http', auth="public", website=True)
    def portal_loyalty_order_page(self, order_id, **kwargs):
        kwargs['page_name'] = 'loyalty'
        return self.portal_order_page(order_id=order_id, **kwargs)
