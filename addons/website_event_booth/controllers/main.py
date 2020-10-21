# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventBoothController(WebsiteEventController):

    @http.route(['/event/<model("event.event"):event>/booths/register'],
                type='http', auth='public', website=True, sitemap=False)
    def event_booth_register(self, event, **kwargs):
        # TODO: Check for public users access rights
        event = event.sudo()
        values = {
            'event': event,
            'main_object': event,
        }
        return request.render('website_event_booth.event_booth_registration', values)

    @http.route(['/event/<model("event.event"):event>/booths/registration/new'],
                type='json', auth='public', methods=['POST'], website=True)
    def booth_registration_new(self, event, **kwargs):
        slots = kwargs.get('event_booth_slot_ids')
        requested_slot_ids = request.env['event.booth.slot'].sudo().browse(slots)
        unavailable_slots = False
        if not requested_slot_ids.is_available():
            unavailable_slots = list(dict(
                                    booth=slot.event_booth_id.name,
                                    name=slot.display_name,
                                ) for slot in requested_slot_ids._get_unavailable_slots())
        details = {}
        if not request.env.user._is_public():
            details = {
                'name': request.env.user.name,
                'email': request.env.user.email,
                'phone': request.env.user.phone,
                'mobile': request.env.user.mobile,
            }
        return {
            'requested_slots': requested_slot_ids.ids,
            'unavailable_slots': unavailable_slots,
            'details': details,
        }

    @http.route(['/event/<model("event.event"):event>/booths/registration/confirm'],
                type='http', auth='public', methods=['POST'], website=True)
    def event_booth_confirm(self, event, **kwargs):
        # transform comma separated number string into an int list
        slots = list(map(int, kwargs.get('event_booth_slot_ids').split(',')))
        slot_ids = request.env['event.booth.slot'].sudo().browse(slots)
        registration_to_create = self._get_contact_details(kwargs)
        registration_to_create.update({'booth_slot_ids': slot_ids.ids})
        registration = request.env['event.booth.registration'].sudo().create(registration_to_create)
        if registration:
            return request.render('website_event_booth.event_booth_registration_complete', {
                'event': event,
                'contact': registration_to_create,
            })
        # TODO: Faut-il confirmer la réservation ici ? ou cela est fait manuellement par l'event manager ?
        return False

    def _get_contact_details(self, contact_details):
        partner_id = request.env.user.partner_id
        if request.env.user._is_public:
            partner_id = request.env['res.partner'].sudo().create({
                'name': contact_details.get('name'),
                'email': contact_details.get('email'),
                'phone': contact_details.get('phone'),
                'mobile': contact_details.get('mobile'),
            })
        return {
            'partner_id': partner_id.id,
            'contact_name': contact_details.get('name'),
            'contact_email': contact_details.get('email'),
            'contact_phone': contact_details.get('phone'),
            'contact_mobile': contact_details.get('mobile'),
        }

    @http.route(['/event/booths/slots'], type='json', auth='public')
    def get_event_booths(self, event_id, booth_category_id):
        booth_ids = request.env['event.booth'].sudo().search([
            ('event_id', '=', int(event_id)),
            ('booth_category_id', '=', int(booth_category_id)),
            ('state', '=', 'available')])

        available_booths = [{
            'id': booth.id,
            'name': booth.name,
            'slot_ids': [{
                'id': slot.id,
                'display_name': slot.display_name
            } for slot in booth.booth_slot_ids if slot.state == 'available']
        } for booth in booth_ids]

        return available_booths
