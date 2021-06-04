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
        if not booth_values.get('partner_email'):
            booth_values['partner_email'] = kwargs.get('sponsor_email')
        if not booth_values.get('partner_name'):
            booth_values['partner_name'] = kwargs.get('sponsor_name')
        if not booth_values.get('partner_phone'):
            booth_values['partner_phone'] = kwargs.get('sponsor_phone')

        booth_values.update(**self._prepare_booth_registration_sponsor_values(event, booth_values, kwargs))
        return booth_values

    def _prepare_booth_registration_sponsor_values(self, event, booth_values, kwargs):
        booth_category = request.env['event.booth.category'].sudo().search(
            [('id', 'in', int(kwargs['booth_category_id']))]
        )
        if booth_category.use_sponsor:
            sponsor_values = {
                'email': kwargs.get('sponsor_email') or booth_values.get('partner_email'),
                'event_id': event.id,
                'exhibitor_type': booth_category.exhibitor_type,
                'name': kwargs.get('sponsor_name') or booth_values.get('partner_name'),
                'partner_id': booth_values['partner_id'],
                'phone': kwargs.get('sponsor_phone') or booth_values.get('partner_phone'),
                'sponsor_type_id': booth_category.sponsor_type_id.id,
                'subtitle': kwargs.get('sponsor_slogan'),
                'website_description': kwargs.get('sponsor_description'),
            }
            sponsor = request.env['event.sponsor'].sudo().create(sponsor_values)
            return {
                'sponsor_id': sponsor.id,
            }
        return {}
