# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import datetime
from odoo import _
from odoo.http import request, route

from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventSaleController(WebsiteEventController):

    @route()
    def event_register(self, event, **post):
        if not request.context.get('pricelist'):
            pricelist = request.website.pricelist_id
            if pricelist:
                event = event.with_context(pricelist=pricelist.id)
        return super().event_register(event, **post)

    def _process_tickets_form(self, event, form_details):
        """ Add price information on ticket order """
        res = super()._process_tickets_form(event, form_details)
        for item in res:
            item['price'] = item['ticket']['price'] if item['ticket'] else 0
        return res

    def _create_attendees_from_registration_post(self, event, registration_data):
        # we have at least one registration linked to a ticket -> sale mode activate
        if not any(info.get('event_ticket_id') for info in registration_data):
            return super()._create_attendees_from_registration_post(event, registration_data)

        order_sudo = request.website.sale_get_order(force_create=True)

        tickets_data = defaultdict(int)
        for data in registration_data:
            event_ticket_id = data.get('event_ticket_id')
            if event_ticket_id:
                tickets_data[event_ticket_id] += 1

        cart_data = {}
        for ticket_id, count in tickets_data.items():
            ticket_sudo = request.env['event.event.ticket'].sudo().browse(ticket_id)
            cart_values = order_sudo._cart_update(
                product_id=ticket_sudo.product_id.id,
                add_qty=count,
                event_ticket_id=ticket_id,
            )
            cart_data[ticket_id] = cart_values['line_id']

        for data in registration_data:
            event_ticket_id = data.get('event_ticket_id')
            if event_ticket_id:
                data['sale_order_id'] = order_sudo.id
                data['sale_order_line_id'] = cart_data[event_ticket_id]

        request.session['website_sale_cart_quantity'] = order_sudo.cart_quantity

        return super()._create_attendees_from_registration_post(event, registration_data)

    @route()
    def registration_confirm(self, event, **post):
        res = super().registration_confirm(event, **post)

        registrations = self._process_attendees_form(event, post)

        # we have at least one registration linked to a ticket -> sale mode activate
        if any(info['event_ticket_id'] for info in registrations):
            order_sudo = request.website.sale_get_order()
            if order_sudo.amount_total:
                return request.redirect("/shop/checkout")
            # free tickets -> order with amount = 0: auto-confirm, no checkout
            elif order_sudo:
                order_sudo.action_confirm()  # tde notsure: email sending ?
                request.website.sale_reset()

        return res

    def _prepare_event_values(self, name, event_start, event_end, address_values=None):
        values = super()._prepare_event_values(name, event_start, event_end, address_values)
        product = request.env.ref('event_sale.product_product_event', raise_if_not_found=False)
        if product:
            values.update({
                'event_ticket_ids': [[0, 0, {
                    'name': _('Registration'),
                    'product_id': product.id,
                    'end_sale_datetime': False,
                    'seats_max': 1000,
                    'price': 0,
                }]]
            })
        return values

    @route(['/website_event_sale/ticket/<int:event_ticket_id>/unit_price/render'],
           type='json', auth="public", website=True, sitemap=False)
    def render_ticket_unit_price(self, event_ticket_id, quantity=1):
        """ Render ticket price.

        :param: int event_ticket_id: id of an event ticket
        :param: int quantity: optional quantity (default 1)
        :return MarkupSafe: rendered price
        """
        website = request.website.get_current_website()
        website_pricelist = website.get_current_pricelist()
        event_ticket = request.env['event.event.ticket'].browse(event_ticket_id).with_context({
            'quantity': quantity,
            'pricelist': website_pricelist.id if website_pricelist else None,
        })
        ticket_currency = event_ticket.currency_id
        now = datetime.date.today()

        if website.company_id.show_line_subtotals_tax_selection == 'tax_excluded':
            price = event_ticket.price_reduce
            price_not_reduced = event_ticket.price
        else:
            price = event_ticket.price_reduce_taxinc
            price_not_reduced = event_ticket.price_incl

        return request.env['ir.qweb']._render('website_event_sale.event_ticket_price', {
            'price': ticket_currency._convert(price, website.currency_id, website.company_id, now),
            'price_not_reduced': ticket_currency._convert(price_not_reduced,
                                                          website.currency_id, website.company_id, now),
            'currency': website.currency_id,
            'discount_policy': website_pricelist.discount_policy if website_pricelist else None,
        })
