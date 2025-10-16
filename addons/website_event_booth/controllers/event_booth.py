# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import werkzeug
from werkzeug.exceptions import Forbidden, NotFound

from odoo import http, tools
from odoo.http import request
from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventBoothController(WebsiteEventController):

    @http.route('/event/<model("event.event"):event>/booth', type='http', auth='public', website=True, sitemap=False)
    def event_booth_main(self, event, booth_category_id=False, booth_ids=False):
        if not event.has_access('read'):
            raise Forbidden()

        booth_category_id = int(booth_category_id) if booth_category_id else False
        return request.render(
            'website_event_booth.event_booth_registration',
            self._prepare_booth_main_values(event, booth_category_id=booth_category_id, booth_ids=booth_ids) | {'seo_object': event.booth_menu_ids}
        )

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

        return request.render(
            'website_event_booth.event_booth_registration_details',
            self._prepare_booth_contact_form_values(event, booth_ids, booth_category_id)
        )

    def _prepare_booth_contact_form_values(self, event, booth_ids, booth_category_id):
        booth_category = request.env['event.booth.category'].sudo().browse(int(booth_category_id))
        event_booths = request.env['event.booth'].sudo().browse([int(booth_id) for booth_id in booth_ids.split(',')])
        default_contact = {}

        if not request.env.user._is_public():
            default_contact = {
                'name': request.env.user.partner_id.name,
                'email': request.env.user.partner_id.email,
                'phone': request.env.user.partner_id.phone,
            }
        else:
            visitor = request.env['website.visitor']._get_visitor_from_request()
            if visitor.email:
                default_contact = {
                    'name': visitor.name,
                    'email': visitor.email,
                    'mobile': visitor.mobile,
                }

        return {
            'booth_category': booth_category,
            'default_contact': default_contact,
            'event': event.sudo(),
            'event_booths': event_booths,
            'hide_sponsors': True,
            'redirect_url': werkzeug.urls.url_quote(request.httprequest.full_path),
            'slots': event.event_slot_ids._filter_open_slots().grouped('date'),
        }

    @http.route('/event/<model("event.event"):event>/booth/confirm',
                type='http', auth='public', methods=['POST'], website=True, sitemap=False)
    def event_booth_registration_confirm(self, event, booth_category_id, event_booth_ids, **kwargs):
        booths = self._get_requested_booths(event, event_booth_ids)

        error_code = self._check_booth_registration_values(booths, kwargs['contact_email'])
        if error_code:
            return json.dumps({'error': error_code})

        booth_values = self._prepare_booth_registration_values(event, kwargs)
        booths.action_confirm(booth_values)

        return self._prepare_booth_registration_success_values(event.name, booth_values)

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

    def _check_booth_registration_values(self, booths, contact_email, booth_category=False):
        if not booths:
            return 'boothError'

        if booth_category and not booth_category.exists():
            return 'boothCategoryError'

        email_normalized = tools.email_normalize(contact_email)
        if request.env.user._is_public() and email_normalized:
            partner = request.env['res.partner'].sudo().search([
                ('email_normalized', '=', email_normalized)
            ], limit=1)
            if partner:
                return 'existingPartnerError'

        return False

    def _prepare_booth_main_values(self, event, booth_category_id=False, booth_ids=False):
        event_sudo = event.sudo()
        available_booth_categories = event_sudo.event_booth_category_available_ids
        chosen_booth_category = available_booth_categories.filtered(lambda cat: cat.id == booth_category_id)
        default_booth_category = available_booth_categories[0] if available_booth_categories else request.env['event.booth.category']
        return {
            'available_booth_category_ids': available_booth_categories,
            'event': event_sudo,
            'event_booths': event_sudo.event_booth_ids,
            'hide_sponsors': True,
            'main_object': event_sudo,
            'selected_booth_category_id': (chosen_booth_category or default_booth_category).id,
            'selected_booth_ids': booth_ids if booth_category_id == chosen_booth_category.id and booth_ids else False,
            'slots': event.event_slot_ids._filter_open_slots().grouped('date'),
        }

    def _prepare_booth_registration_values(self, event, kwargs):
        return self._prepare_booth_registration_partner_values(event, kwargs)

    def _prepare_booth_registration_partner_values(self, event, kwargs):
        if request.env.user._is_public():
            contact_email_normalized = tools.email_normalize(kwargs['contact_email'])
            if contact_email_normalized:
                partner = event.sudo()._partner_find_from_emails_single(
                    [contact_email_normalized],
                    additional_values={contact_email_normalized: {
                        'phone': kwargs.get('contact_phone'),
                        'name': kwargs.get('contact_name'),
                    }},
                )
            else:
                partner = request.env['res.partner']
        else:
            partner = request.env.user.partner_id
        return {
            'partner_id': partner.id,
            'contact_name': kwargs.get('contact_name') or partner.name,
            'contact_email': kwargs.get('contact_email') or partner.email,
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
            },
        })

    @http.route('/event/booth/check_availability', type='jsonrpc', auth='public', methods=['POST'])
    def check_booths_availability(self, event_booth_ids=None):
        if not event_booth_ids:
            return {}
        booths = request.env['event.booth'].sudo().browse(event_booth_ids)
        return {
            'unavailable_booths': booths.filtered(lambda booth: not booth.is_available).ids
        }

    @http.route(['/event/booth_category/get_available_booths'], type='jsonrpc', auth='public')
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
