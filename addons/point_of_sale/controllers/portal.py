# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import http
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class PosCustomerPortal(CustomerPortal):

    def _prepare_portal_counter_values(self, counter):
        partner = self.env.user.partner_id
        if counter == 'pos_order_count':
            return 'pos.order', self._prepare_pos_orders_domain(partner), 'read'
        return super()._prepare_portal_counter_values(counter)

    def _prepare_pos_orders_domain(self, partner):
        return [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['paid', 'done']),
        ]

    def _get_pos_searchbar_sortings(self):
        return {
            'date': {'label': self.env._('Order Date'), 'order': 'date_order desc'},
            'total_amount': {'label': self.env._('Total'), 'order': 'amount_total desc'},
        }

    def _get_pos_searchbar_filters(self):
        return {
            'all': {'label': self.env._('All'), 'domain': []},
            'invoiced_order': {
                'label': self.env._('Invoiced'),
                'domain': [('is_singly_invoiced', '=', True)]
            },
            'non_invoiced_order': {
                'label': self.env._('Not Invoiced'),
                'domain': [('is_singly_invoiced', '=', False)]
            },
        }

    def _prepare_pos_order_portal_rendering_values(
        self,
        page=1,
        sortby='date',
        filterby='all',
        **kwargs,
    ):
        PosOrder = self.env['pos.order']

        values = self._prepare_portal_layout_values()
        domain = self._prepare_pos_orders_domain(self.env.user.partner_id)

        searchbar_sortings = self._get_pos_searchbar_sortings()
        searchbar_filters = self._get_pos_searchbar_filters()

        sortby = sortby if sortby in searchbar_sortings else 'date'
        filterby = filterby if filterby in searchbar_filters else 'all'

        domain += searchbar_filters[filterby]['domain']
        sort_order = searchbar_sortings[sortby]['order']
        url_args = {'filterby': filterby}
        if len(searchbar_sortings) > 1:
            url_args['sortby'] = sortby

        url = '/my/store-orders'
        pager_values = portal_pager(
            url=url,
            total=PosOrder.search_count(domain) if PosOrder.has_access('read') else 0,
            page=page,
            step=self._items_per_page,
            url_args=url_args,
        )
        pos_orders = (
            PosOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager_values['offset'])
            if PosOrder.has_access('read')
            else PosOrder
        )
        values.update({
            'pos_orders': pos_orders,
            'page_name': 'store_order',
            'pager': pager_values,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': url,
        })
        if len(searchbar_sortings) > 1:
            values.update({'sortby': sortby, 'searchbar_sortings': searchbar_sortings})
        return values

    @http.route(['/my/store-orders', '/my/store-orders/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_pos_orders(self, **kwargs):
        values = self._prepare_pos_order_portal_rendering_values(**kwargs)
        request.session['my_store_orders_history'] = values['pos_orders'].ids[:100]
        return request.render('point_of_sale.portal_my_pos_orders', values)
