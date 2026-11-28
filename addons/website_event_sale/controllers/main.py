# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from collections import defaultdict

from odoo import Command
from odoo.http import request, route
from odoo.tools import float_is_zero

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.website_event.controllers.main import WebsiteEventController

# checkbox name in the attendee form: ticket_option_<attendee index>_<product id>
OPTION_INPUT_RE = re.compile(r'ticket_option_(\d+)_(\d+)')


class WebsiteEventSaleController(WebsiteEventController):

    def _process_attendees_form(self, event, form_details):
        """ Turn the ticked option checkboxes into ``ticket_option_product_ids`` on each
        attendee's registration values.

        Checkboxes are regrouped under a ``<index>-ticket_option_product_ids`` key so that the
        core parser attaches them to the right attendee, then checked against the options really
        offered by the attendee's ticket.
        """
        form_details = dict(form_details)
        options_per_attendee = defaultdict(list)
        for key, value in form_details.items():
            match = OPTION_INPUT_RE.fullmatch(key)
            if match and value:
                options_per_attendee[match[1]].append(match[2])
        # never trust a directly posted value for the field
        for key in [key for key in form_details if key.endswith('-ticket_option_product_ids')]:
            del form_details[key]
        for index, product_ids in options_per_attendee.items():
            form_details[f'{index}-ticket_option_product_ids'] = ','.join(product_ids)

        registrations = super()._process_attendees_form(event, form_details)

        tickets_sudo = request.env['event.event.ticket'].sudo()
        for registration in registrations:
            raw_ids = registration.pop('ticket_option_product_ids', '')
            if not raw_ids:
                continue
            asked_ids = {int(product_id) for product_id in raw_ids.split(',')}
            ticket = tickets_sudo.browse(registration.get('event_ticket_id') or [])
            options = ticket.optional_product_ids.filtered(lambda product: product.id in asked_ids)
            if options:
                registration['ticket_option_product_ids'] = [Command.set(options.ids)]
        return registrations

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

        event_ticket_ids = [registration['event_ticket_id'] for registration in registration_data if registration.get('event_ticket_id')]
        event_ticket_by_id = {
            event_ticket.id: event_ticket
            for event_ticket in request.env['event.event.ticket'].sudo().browse(event_ticket_ids)
        }

        has_options = any(data.get('ticket_option_product_ids') for data in registration_data)
        if (
            all(event_ticket.total_price == 0 for event_ticket in event_ticket_by_id.values())
            and not request.cart.id
            and not has_options
        ):
            # all chosen tickets are free AND no existing SO AND no option -> skip SO and payment process
            return super()._create_attendees_from_registration_post(event, registration_data)

        order_sudo = request.cart or self.env.website._create_cart()
        tickets_data = defaultdict(int)
        for data in registration_data:
            event_slot_id = data.get('event_slot_id', False)
            event_ticket_id = data.get('event_ticket_id', False)
            if event_ticket_id:
                tickets_data[event_slot_id, event_ticket_id] += 1

        cart_data = {}
        for (slot_id, ticket_id), count in tickets_data.items():
            ticket_sudo = event_ticket_by_id.get(ticket_id)
            cart_values = order_sudo._cart_add(
                product_id=ticket_sudo.product_id.id,
                quantity=count,
                event_ticket_id=ticket_id,
                event_slot_id=slot_id,
            )
            for product in ticket_sudo.additional_product_ids:
                order_sudo._cart_add(
                    product_id=product.id,
                    quantity=count,
                    linked_line_id=cart_values['line_id'],
                )
            cart_data[slot_id, ticket_id] = cart_values['line_id']

        for data in registration_data:
            event_slot_id = data.get('event_slot_id', False)
            event_ticket_id = data.get('event_ticket_id', False)
            event_ticket = event_ticket_by_id.get(event_ticket_id)
            if event_ticket:
                data['sale_order_id'] = order_sudo.id
                data['sale_order_line_id'] = cart_data[event_slot_id, event_ticket_id]

        return super()._create_attendees_from_registration_post(event, registration_data)

    @route()
    def registration_confirm(self, event, **post):
        res = super().registration_confirm(event, **post)

        registrations = self._process_attendees_form(event, post)
        order_sudo = request.cart
        if not any(line.event_ticket_id for line in order_sudo.order_line):
            # order does not contain any tickets, meaning we are confirming a free event
            return res

        # we have at least one registration linked to a ticket -> sale mode activate
        if any(info['event_ticket_id'] for info in registrations):
            # free tickets -> order with amount = 0: auto-confirm, no checkout
            if all(line.event_ticket_id and float_is_zero(line.event_ticket_id.price, precision_digits=2) for line in order_sudo.order_line):
                order_sudo.action_confirm()  # tde notsure: email sending ?
                self.env.website.sale_reset()
                request.session['sale_last_order_id'] = order_sudo.id
                return request.redirect("/shop/confirmation")
            elif order_sudo:
                signup_required = (
                    request.env.user._is_public()
                    and self.env.website.account_on_checkout == 'mandatory'
                )
                # Skip pre-creating a partner when signup will create one itself.
                if order_sudo._is_anonymous_cart() and not signup_required:
                    booked_by_partner, feedback_dict = CustomerPortal()._create_or_update_address(
                        request.env['res.partner'].sudo().with_context(partial_address_before_checkout=True),
                        order_sudo=order_sudo,
                        **registrations[0]
                    )
                    if not feedback_dict.get('invalid_fields'):
                        order_sudo._update_address(booked_by_partner.id, ['partner_id'])
                request.session['sale_last_order_id'] = order_sudo.id
                return request.redirect("/shop/checkout?try_skip_step=true")
        return res
