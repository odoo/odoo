# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventBoothController(WebsiteEventController):

    @http.route()
    def event_booth_confirm(self, event, **kwargs):
        slots = list(map(int, kwargs.get('event_booth_slot_ids').split(',')))
        slot_ids = request.env['event.booth.slot'].sudo().browse(slots)
        # TODO: ajouter booth_category_id au form
        product_id = slot_ids.event_booth_id.booth_category_id.product_id
        order = request.website.sale_get_order(force_create=1)
        order.with_context(event_booth_slot_ids=slot_ids.ids)._cart_update(
            product_id=product_id.id,
            add_qty=1
        )
        return request.redirect('/shop/checkout')
        # category_id = int(kwargs.get('booth_category_id'))
        # booth_category_id = request.env['event.booth.category'].sudo().browse(category_id)
        # slot_ids = [int(x) for x in request.httprequest.form.getlist('event_booth_slot_ids')]
        # slots = request.env['event.booth.slot'].sudo().browse(slot_ids)
        # order = request.website.sale_get_order(force_create=1)
        # order.with_context(event_booth_slot_ids=slots.ids)._cart_update(product_id=booth_category_id.product_id.id, add_qty=1)
        # return request.redirect('/shop/checkout')
