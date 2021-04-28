# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        if 'loyalty_points' in counters:
            values['loyalty_points'] = int(partner.loyalty_points) if partner.loyalty_points.is_integer() else partner.loyalty_points
        return values

    # ------------------------------------------------------------
    # My Loyalty
    # ------------------------------------------------------------

    @http.route(['/my/loyalty', '/my/loyalty/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_loyalty(self, page=1, tab='rewards_catalog', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        if tab == 'rewards_catalog':
            reward_ids = request.website.loyalty_id.website_reward_ids.sorted('point_cost')
            # pager
            pager = portal_pager(
                url="/my/loyalty",
                url_args={tab: 'rewards_catalog'},
                total=len(reward_ids),
                page=page,
                step=self._items_per_page,
            )
            # content according to pager
            reward_ids = reward_ids[pager['offset']:pager['offset'] + self._items_per_page]

            values.update({
                'rewards': reward_ids,
            })
        elif tab == 'won_points_history':
            SaleOrder = request.env['sale.order']

            domain = [
                ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
                ('state', 'in', ['sent', 'sale', 'done']),
                ('website_id', '=', request.website.id),
                ('won_loyalty_points', '>', 0),
            ]

            # count for pager
            order_count = SaleOrder.search_count(domain)
            # pager
            pager = portal_pager(
                url="/my/loyalty",
                url_args={tab: 'won_points_history'},
                total=order_count,
                page=page,
                step=self._items_per_page,
            )
            # content according to pager
            orders = SaleOrder.search(domain, order='date_order desc', limit=self._items_per_page, offset=pager['offset'])
            request.session['my_loyalty_history'] = orders.ids[:100]

            values.update({
                'orders': orders.sudo(),
                'default_url': '/my/orders',
            })
        else:  # tab == 'redeem_history'
            reward_ids = partner.sudo().loyalty_website_redeemed_reward_ids.filtered(
                lambda reward: reward.website_id == request.website).sorted('create_date', reverse=True)
            # pager
            pager = portal_pager(
                url="/my/loyalty",
                url_args={tab: 'redeem_history'},
                total=len(reward_ids),
                page=page,
                step=self._items_per_page,
            )
            # content according to pager
            reward_ids = reward_ids[pager['offset']:pager['offset'] + self._items_per_page]

            values.update({
                'redeemed_rewards': reward_ids,
            })

        values.update({
            'partner': partner,
            'page_name': 'loyalty',
            'pager': pager,
            'tab': tab,
        })
        return request.render("website_sale_loyalty.portal_my_loyalty", values)

    @http.route(['/my/loyalty/<int:order_id>'], type='http', auth="public", website=True)
    def portal_loyalty_order_page(self, order_id, **kwargs):
        kwargs['page_name'] = 'loyalty'
        return self.portal_order_page(order_id=order_id, **kwargs)

    @http.route('/my/loyalty/redeem', type='json', auth="user", website=True)
    def portal_loyalty_redeem_reward(self, reward_id):
        reward_id = request.env['loyalty.website.reward'].browse(int(reward_id)) if reward_id else None
        if not reward_id or reward_id.loyalty_program_id != request.website.loyalty_id:
            return {'error': _('Website has no such reward')}
        try:
            gift_card_id = reward_id._redeem_gift_card(request.website)
            return {'code': gift_card_id.code}
        except UserError as error:
            return {'error': str(error)}
