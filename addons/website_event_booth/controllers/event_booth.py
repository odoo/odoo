# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventBoothController(WebsiteEventController):

    @http.route('/event/<model("event.event"):event>/booth', type='http', auth='public', website=True, sitemap=False)
    def event_booth_main(self, event, **kwargs):
        event_sudo = event.sudo()
        available_booth_ids = event_sudo.event_booth_ids.filtered(lambda booth: booth.is_available)
        available_booth_category_ids = available_booth_ids.mapped('booth_category_id')
        values = {
            'main_object': event,
            'event': event,
            'available_booth_ids': available_booth_ids,
            'available_booth_category_ids': available_booth_category_ids,
        }
        return request.render('website_event_booth.event_booth_registration', values)

    @http.route('/event/<model("event.event"):event>/booth/register', type='http', auth='public', methods=['POST'], website=True)
    def event_booth_register(self, event, **kwargs):
        event_booth_ids = request.httprequest.form.getlist('event_booth_ids')
        booth_category = int(kwargs.get('booth_category_id'))
        booth_category_id = request.env['event.booth.category'].sudo().browse(booth_category)
        kwargs['event_booth_ids'] = ','.join(event_booth_ids)
        if not self._booth_registration_details_complete(booth_category_id):
            return request.render(
                'website_event_booth.event_booth_registration_details',
                {'event': event.sudo(),
                 'booth_category_id': booth_category_id,
                 'event_booth_ids': kwargs.get('event_booth_ids'),
                }
            )
        return self.booth_registration_confirm(event, **kwargs)

    def _booth_registration_details_complete(self, booth_category_id):
        """
        Should be overriden to test if other details has to be filled
        such as the sponsor informations in website_event_booth_exhibitor
        :return:
        """
        return not request.env.user._is_public()

    @http.route('/event/<model("event.event"):event>/booth/confirm', type='http', auth='public', methods=['POST'], website=True)
    def event_booth_registration_confirm(self, event, **kwargs):
        booth_ids = list(map(int, kwargs.get('event_booth_ids').split(',')))
        booths = self.env['event.booth'].sudo().search([
            ('event_id', '=', event.id),
            ('state', '=', 'available')
        ])
        if booth_ids != booths.ids:
            raise Forbidden()  # tde todo: fixme

        booth_values = self._prepare_booth_registration_values(event, kwargs)
        booths.action_confirm(booth_values)

        return request.render(
            'website_event_booth.event_booth_registration_complete',
            {'event': event,
             'partner': booths.partner_id,
            }
        )

    def _prepare_booth_registration_values(self, event, kwargs):
        return {
            'partner_id': self._get_partner(kwargs)
        }

    def _get_partner(self, kwargs):
        if request.env.user._is_public():
            return request.env['res.partner'].sudo().create({
                'name': kwargs.get('contact_name'),
                'email': kwargs.get('contact_email'),
                'phone': kwargs.get('contact_phone'),
                'mobile': kwargs.get('contact_mobile'),
            }).id
        return request.env.user.partner_id.id

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
