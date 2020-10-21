# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import werkzeug
from werkzeug.exceptions import Forbidden, NotFound

from odoo import exceptions, http, _
from odoo.http import request
from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventBoothController(WebsiteEventController):

    @http.route('/event/<model("event.event"):event>/booth', type='http', auth='public', website=True, sitemap=True)
    def event_booth_main(self, event):
        try:
            event.check_access_rights('read')
            event.check_access_rule('read')
        except exceptions.AccessError:
            raise Forbidden()

        event_sudo = event.sudo()
        values = {
            'event': event_sudo,
            'event_booths': event_sudo.event_booth_ids,
            'available_booth_category_ids': event_sudo.event_booth_category_available_ids,
            'main_object': event,
        }
        return request.render('website_event_booth.event_booth_registration', values)

    @http.route('/event/<model("event.event"):event>/booth/register',
                type='http', auth='public', methods=['POST'], website=True, sitemap=False)
    def event_booth_register(self, event, booth_category_id):
        event_booth_ids = request.httprequest.form.getlist('event_booth_ids')

        return request.redirect(('/event/%s/booth/register_form?' % event.id) + werkzeug.urls.url_encode({
            'booth_ids': ','.join(event_booth_ids),
            'booth_category_id': int(booth_category_id),
        }))

    @http.route('/event/<model("event.event"):event>/booth/register_form',
                type='http', auth='public', methods=['GET'], website=True, sitemap=False)
    def event_booth_contact_form(self, event, booth_ids=None, booth_category_id=None):
        if not booth_ids or not booth_category_id:
            raise NotFound()

        booth_category = request.env['event.booth.category'].sudo().browse(int(booth_category_id))
        event_booths = request.env['event.booth'].sudo().browse([int(booth_id) for booth_id in booth_ids.split(',')])
        default_contact = {}
        if not request.env.user._is_public():
            default_contact = {
                'name': request.env.user.partner_id.name,
                'email': request.env.user.partner_id.email,
                'phone': request.env.user.partner_id.phone,
                'mobile': request.env.user.partner_id.mobile,
            }
        else:
            visitor = request.env['website.visitor']._get_visitor_from_request()
            if visitor.email:
                default_contact = {
                    'name': visitor.name,
                    'email': visitor.email,
                    'mobile': visitor.mobile,
                }
        return request.render(
            'website_event_booth.event_booth_registration_details',
            {'event': event.sudo(),
             'default_contact': default_contact,
             'booth_category': booth_category,
             'event_booths': event_booths,
            }
        )

    def _get_requested_booths(self, event, event_booth_ids):
        booth_ids = json.loads(event_booth_ids)
        booths = request.env['event.booth'].sudo().search([
            ('event_id', '=', event.id),
            ('state', '=', 'available'),
            ('id', 'in', booth_ids)
        ])
        if booth_ids != booths.ids:
            raise Forbidden(_('Booth registration failed. Please try again.'))
        if len(booths.booth_category_id) != 1:
            raise Forbidden(_('Booths should belong to the same category.'))
        return booths

    @http.route('/event/<model("event.event"):event>/booth/confirm',
                type='http', auth='public', methods=['POST'], website=True, sitemap=False)
    def event_booth_registration_confirm(self, event, booth_category_id, event_booth_ids, **kwargs):
        booths = self._get_requested_booths(event, event_booth_ids)

        booth_values = self._prepare_booth_registration_values(event, kwargs)
        booths.action_confirm(booth_values)

        return request.redirect(('/event/%s/booth/success?' % event.id) + werkzeug.urls.url_encode({
            'booths': ','.join([str(id) for id in booths.ids]),
        }))

    # This will be removed soon
    @http.route('/event/<model("event.event"):event>/booth/success',
                type='http', auth='public', methods=['GET'], website=True, sitemap=False)
    def event_booth_registration_complete(self, event, booths):
        booth_ids = request.env['event.booth'].sudo().search([
            ('event_id', '=', event.id),
            ('state', '=', 'unavailable'),
            ('id', 'in', [int(id) for id in booths.split(',')]),
        ])
        if len(booth_ids.mapped('partner_id')) > 1:
            raise NotFound()
        event_sudo = event.sudo()
        return request.render(
            'website_event_booth.event_booth_registration_complete',
            {'event': event,
             'event_booths': event_sudo.event_booth_ids,
             'main_object': event,
             'contact_name': booth_ids[0].contact_name or booth_ids.partner_id.name,
             'contact_email': booth_ids[0].contact_email or booth_ids.partner_id.email,
             'contact_mobile': booth_ids[0].contact_mobile or booth_ids.partner_id.mobile,
             'contact_phone': booth_ids[0].contact_phone or booth_ids.partner_id.phone,
             }
        )

    def _prepare_booth_registration_values(self, event, kwargs):
        return self._prepare_booth_registration_partner_values(event, kwargs)

    def _prepare_booth_registration_partner_values(self, event, kwargs):
        if request.env.user._is_public():
            contact_email = kwargs['contact_email']
            partner = request.env['res.partner'].sudo().find_or_create(contact_email)
            if not partner.name and kwargs.get('contact_name'):
                partner.name = kwargs['contact_name']
            if not partner.phone and kwargs.get('contact_phone'):
                partner.phone = kwargs['contact_phone']
            if not partner.mobile and kwargs.get('contact_mobile'):
                partner.mobile = kwargs['contact_mobile']
        else:
            partner = request.env.user.partner_id
        return {
            'partner_id': partner.id,
            'contact_name': kwargs.get('contact_name') or partner.name,
            'contact_email': kwargs.get('contact_email') or partner.email,
            'contact_mobile': kwargs.get('contact_mobile') or partner.mobile,
            'contact_phone': kwargs.get('contact_phone') or partner.phone,
        }

    @http.route('/event/booth/check_availability', type='json', auth='public', methods=['POST'])
    def check_booths_availability(self, event_booth_ids=None):
        if not event_booth_ids:
            return {}
        booths = request.env['event.booth'].sudo().browse(event_booth_ids)
        return {
            'unavailable_booths': booths.filtered(lambda booth: not booth.is_available).ids
        }

    @http.route(['/event/booth_category/get_available_booths'], type='json', auth='public')
    def get_booth_category_available_booths(self, event_id, booth_category_id):
        booth_ids = request.env['event.booth'].sudo().search([
            ('event_id', '=', int(event_id)),
            ('booth_category_id', '=', int(booth_category_id)),
            ('state', '=', 'available')
        ])

        return [
            {'id': booth.id, 'name': booth.name}
            for booth in booth_ids
        ]
