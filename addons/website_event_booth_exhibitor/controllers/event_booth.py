# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventBoothController(WebsiteEventController):

    def _prepare_booth_registration_values(self, event, kwargs):
        values = super(WebsiteEventBoothController, self)._prepare_booth_registration_values(event, kwargs)
        sponsor_id = self._create_sponsor(event, values.get('partner_id'), kwargs)
        if sponsor_id:
            values.update({
                'sponsor_id': sponsor_id,
            })
        return values

    def _booth_registration_details_complete(self, booth_category_id):
        if booth_category_id.use_sponsor:
            return False
        return super(WebsiteEventBoothController, self)._booth_registration_details_complete(booth_category_id)

    def _get_partner(self, kwargs):
        if request.env.user._is_public():
            return request.env['res.partner'].sudo().create({
                'name': kwargs.get('contact_name') or kwargs.get('sponsor_name'),
                'email': kwargs.get('contact_email') or kwargs.get('sponsor_email'),
                'phone': kwargs.get('contact_phone') or kwargs.get('sponsor_phone'),
                'mobile': kwargs.get('contact_mobile'),
            }).id
        return request.env.user.partner_id.id

    def _get_sponsor_details(self, partner, kwargs):
        values = {
            'partner_id': partner,
            'name': kwargs.get('sponsor_name'),
            'email': kwargs.get('sponsor_email'),
            'phone': kwargs.get('sponsor_phone'),
            'subtitle': kwargs.get('sponsor_slogan'),
            'website_description': kwargs.get('sponsor_description'),
        }
        return values

    def _create_sponsor(self, event, partner, kwargs):
        booth_category = int(kwargs.get('booth_category_id'))
        booth_category_id = request.env['event.booth.category'].sudo().browse(booth_category)
        if booth_category_id.use_sponsor:
            sponsor = self._get_sponsor_details(partner, kwargs)
            sponsor.update({
                'event_id': event.id,
                'sponsor_type_id': booth_category_id.sponsor_type_id.id,
                'exhibitor_type': booth_category_id.exhibitor_type,
                'active': False,
            })
            return request.env['event.sponsor'].sudo().create(sponsor)
        return False
