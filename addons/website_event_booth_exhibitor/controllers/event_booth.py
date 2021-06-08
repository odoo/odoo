# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventBoothController(WebsiteEventController):

    def _booth_registration_details_complete(self, booth_category_id):
        if booth_category_id.use_sponsor:
            return False
        return super(WebsiteEventBoothController, self)._booth_registration_details_complete(booth_category_id)

    def _prepare_booth_registration_values(self, event, kwargs):
        booth_values = super(WebsiteEventBoothController, self)._prepare_booth_registration_values(event, kwargs)
        if not booth_values.get('contact_email'):
            booth_values['contact_email'] = kwargs.get('sponsor_email')
        if not booth_values.get('contact_name'):
            booth_values['contact_name'] = kwargs.get('sponsor_name')
        if not booth_values.get('contact_mobile'):
            booth_values['contact_mobile'] = kwargs.get('sponsor_mobile')
        if not booth_values.get('contact_phone'):
            booth_values['contact_phone'] = kwargs.get('sponsor_phone')

        booth_values.update(**self._prepare_booth_registration_sponsor_values(event, booth_values, kwargs))
        return booth_values

    def _prepare_booth_registration_sponsor_values(self, event, booth_values, kwargs):
        booth_category = request.env['event.booth.category'].sudo().search(
            [('id', '=', int(kwargs['booth_category_id']))]
        )
        if booth_category.use_sponsor:
            sponsor_values = {
                'email': kwargs.get('sponsor_email') or booth_values.get('contact_email'),
                'event_id': event.id,
                'exhibitor_type': booth_category.exhibitor_type,
                'name': kwargs.get('sponsor_name') or booth_values.get('contact_name'),
                'partner_id': booth_values['partner_id'],
                'mobile': kwargs.get('sponsor_mobile') or booth_values.get('contact_mobile'),
                'phone': kwargs.get('sponsor_phone') or booth_values.get('contact_phone'),
                'sponsor_type_id': booth_category.sponsor_type_id.id,
                'subtitle': kwargs.get('sponsor_slogan'),
                'website_description': kwargs.get('sponsor_description'),
            }
            sponsor = request.env['event.sponsor'].sudo().create(sponsor_values)
            return {
                'sponsor_id': sponsor.id,
            }
        return {}
