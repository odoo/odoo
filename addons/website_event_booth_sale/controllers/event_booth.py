# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventBoothController(WebsiteEventController):

    @http.route()
    def event_booth_main(self, event):
        event = event.with_context(pricelist=request.website.id)
        if not request.context.get('pricelist'):
            pricelist = request.website.get_current_pricelist()
            if pricelist:
                event = event.with_context(pricelist=pricelist.id)
        return super(WebsiteEventBoothController, self).event_booth_main(event)

    @http.route()
    def event_booth_registration_confirm(self, event, **kwargs):
        booths = list(map(int, kwargs.get('event_booth_ids').split(',')))
        requested_booth_ids = request.env['event.booth'].sudo().browse(booths)
        booth_category = int(kwargs.get('booth_category_id'))
        booth_category_id = request.env['event.booth.category'].browse(booth_category)
        # values = self._prepare_booth_registration_values(event, kwargs)
        # requested_booth_ids.write(values)
        order = request.website.sale_get_order(force_create=1)
        order.with_context(event_booth_pending_ids=requested_booth_ids.ids)._cart_update(
            product_id=booth_category_id.product_id.id,
            add_qty=1,
        )
        return request.redirect('/shop/checkout')
