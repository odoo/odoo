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
        booth_category = request.env['event.booth.category'].sudo().browse(int(booth_category_id))
        error_code = self._check_booth_registration_values(
            booths,
            kwargs['contact_email'],
            booth_category=booth_category)
        if error_code:
            return json.dumps({'error': error_code})

        booth_values = self._prepare_booth_registration_values(event, kwargs)
        order_sudo = request.website.sale_get_order(force_create=True)
        order_sudo._cart_update(
            product_id=booth_category.product_id.id,
            set_qty=1,
            event_booth_pending_ids=booths.ids,
            registration_values=booth_values,
        )
        if order_sudo.amount_total:
            if request.env.user._is_public():
                order_sudo.partner_id = booth_values['partner_id']
            return json.dumps({'redirect': '/shop/cart'})
        elif order_sudo:
            order_sudo.action_confirm()
            request.website.sale_reset()

            return self._prepare_booth_registration_success_values(event.name, booth_values)
