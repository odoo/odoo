# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.http import request, route
from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventBoothController(WebsiteEventController):

    @route()
    def event_booth_main(self, event):
        pricelist = request.website.pricelist_id
        if pricelist:
            event = event.with_context(pricelist=pricelist.id)
        return super(WebsiteEventBoothController, self).event_booth_main(event)

    @route()
    def event_booth_registration_confirm(self, event, booth_category_id, event_booth_ids, **kwargs):
        """Override: Doesn't call the parent method because we go through the checkout
        process which will confirm the booths when receiving the payment."""
        booths = self._get_requested_booths(event, event_booth_ids)
        if not booths:
            return json.dumps({'error': 'boothError'})

        booth_category = request.env['event.booth.category'].sudo().browse(int(booth_category_id))
        if not booth_category.exists():
            return json.dumps({'error': 'boothCategoryError'})

        booth_values = self._prepare_booth_registration_values(event, kwargs)
        order_sudo = request.website.sale_get_order(force_create=True)
        order_sudo._cart_update(
            product_id=booth_category.product_id.id,
            set_qty=1,
            event_booth_pending_ids=booths.ids,
            registration_values=booth_values,
        )
        if order_sudo.amount_total:
            return json.dumps({'redirect': '/shop/checkout'})
        elif order_sudo:
            order_sudo.action_confirm()
            request.website.sale_reset()

            return self._prepare_booth_registration_success_values(event.name, booth_values)
