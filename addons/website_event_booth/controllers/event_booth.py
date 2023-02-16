# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import werkzeug
from werkzeug.exceptions import Forbidden, NotFound

from odoo import exceptions, http, tools
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
    def event_booth_register(self, event, booth_category_id, event_booth_ids):
        # `event_booth_id` in `requests.params` only contains the first
        # checkbox, we re-parse the form using getlist to get them all
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
        if booth_ids != booths.ids or len(booths.booth_category_id) != 1:
            return request.env['event.booth']
        return booths

    @http.route('/event/<model("event.event"):event>/booth/confirm',
                type='http', auth='public', methods=['POST'], website=True, sitemap=False)
    def event_booth_registration_confirm(self, event, booth_category_id, event_booth_ids, **kwargs):
        booths = self._get_requested_booths(event, event_booth_ids)

        if not booths:
            return json.dumps({'error': 'boothError'})
        booth_values = self._prepare_booth_registration_values(event, kwargs)
        booths.action_confirm(booth_values)

        return self._prepare_booth_registration_success_values(event.name, booth_values)

    def _prepare_booth_registration_values(self, event, kwargs):
        return self._prepare_booth_registration_partner_values(event, kwargs)

    def _prepare_booth_registration_partner_values(self, event, kwargs):
        if request.env.user._is_public():
            contact_name_email = tools.formataddr((kwargs['contact_name'], kwargs['contact_email']))
            partner = request.env['res.partner'].sudo().find_or_create(contact_name_email)
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

    def _prepare_booth_registration_success_values(self, event_name, booth_values):
        return json.dumps({
            'success': True,
            'event_name': event_name,
            'contact': {
                'name': booth_values.get('contact_name'),
                'email': booth_values.get('contact_email'),
                'phone': booth_values.get('contact_phone'),
                'mobile': booth_values.get('contact_mobile'),
            },
        })

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
