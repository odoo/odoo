# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint, sample
from werkzeug.exceptions import NotFound, Forbidden

from odoo import exceptions, http
from odoo.addons.website_event.controllers.main import WebsiteEventController
from odoo.http import request
from odoo.osv import expression
from odoo.tools import format_duration


class ExhibitorController(WebsiteEventController):

    def _get_event_sponsors_base_domain(self, event):
        search_domain_base = [
            ('event_id', '=', event.id),
            ('exhibitor_type', 'in', ['exhibitor', 'online']),
        ]
        if not request.env.user.has_group('event.group_event_registration_desk'):
            search_domain_base = expression.AND([search_domain_base, [('is_published', '=', True)]])
        return search_domain_base

    # ------------------------------------------------------------
    # MAIN PAGE
    # ------------------------------------------------------------

    @http.route([
        # TDE BACKWARD: exhibitors is actually a typo
        '/event/<model("event.event"):event>/exhibitors',
        # TDE BACKWARD: matches event/event-1/exhibitor/exhib-1 sub domain
        '/event/<model("event.event"):event>/exhibitor'
    ], type='http', auth="public", website=True, sitemap=False)
    def event_exhibitors(self, event):
        return request.render(
            "website_event_exhibitor.event_exhibitors",
            self._event_exhibitors_get_values(event)
        )

    def _event_exhibitors_get_values(self, event):
        # init and process search terms
        search_domain = self._get_event_sponsors_base_domain(event)

        # fetch data to display; use sudo to allow reading partner info, be sure domain is correct
        event = event.with_context(tz=event.date_tz or 'UTC')
        sponsors = request.env['event.sponsor'].sudo().search(search_domain)
        sponsor_types = sponsors.mapped('sponsor_type_id')
        sponsor_countries = sponsors.mapped('partner_id.country_id').sorted('name')
        # organize sponsors into categories to help display
        sponsor_categories = dict()
        for sponsor in sponsors:
            if not sponsor_categories.get(sponsor.sponsor_type_id):
                sponsor_categories[sponsor.sponsor_type_id] = request.env['event.sponsor'].sudo()
            sponsor_categories[sponsor.sponsor_type_id] |= sponsor
        sponsor_categories = [
            dict({
                'sponsorship': sponsor_category,
                'sponsors': sample(sponsors, len(sponsors)),
            }) for sponsor_category, sponsors in sponsor_categories.items()]

        # return rendering values
        return {
            # event information
            'event': event,
            'main_object': event,
            'sponsor_categories': sponsor_categories,
            'hide_sponsors': True,
            'sponsor_types': sponsor_types,
            'sponsor_countries': sponsor_countries,
            # environment
            'hostname': request.httprequest.host.split(':')[0],
            'is_event_user': request.env.user.has_group('event.group_event_registration_desk'),
        }

    # ------------------------------------------------------------
    # FRONTEND FORM
    # ------------------------------------------------------------

    @http.route(['''/event/<model("event.event", "[('exhibitor_menu', '=', True)]"):event>/exhibitor/<model("event.sponsor", "[('event_id', '=', event.id)]"):sponsor>'''],
                type='http', auth="public", website=True, sitemap=True)
    def event_exhibitor(self, event, sponsor, **options):
        try:
            sponsor.check_access_rule('read')
        except exceptions.AccessError:
            raise Forbidden()
        sponsor = sponsor.sudo()

        if 'widescreen' not in options and sponsor.chat_room_id and sponsor.is_in_opening_hours:
            options['widescreen'] = True

        return request.render(
            "website_event_exhibitor.event_exhibitor_main",
            self._event_exhibitor_get_values(event, sponsor, **options)
        )

    def _event_exhibitor_get_values(self, event, sponsor, **options):
        # search for exhibitor list
        search_domain_base = self._get_event_sponsors_base_domain(event)
        search_domain_base = expression.AND([
            search_domain_base,
            [('id', '!=', sponsor.id)]
        ])
        sponsors_other = request.env['event.sponsor'].sudo().search(search_domain_base)
        current_country = sponsor.partner_id.country_id

        sponsors_other = sponsors_other.sorted(key=lambda sponsor: (
            sponsor.is_in_opening_hours,
            sponsor.partner_id.country_id == current_country,
            -1 * sponsor.sponsor_type_id.sequence,
            randint(0, 20)
        ), reverse=True)

        option_widescreen = options.get('widescreen', False)
        option_widescreen = bool(option_widescreen) if option_widescreen != '0' else False

        return {
            # event information
            'event': event,
            'main_object': sponsor,
            'sponsor': sponsor,
            'hide_sponsors': True,
            # sidebar
            'sponsors_other': sponsors_other[:30],
            # options
            'option_widescreen': option_widescreen,
            'option_can_edit': request.env.user.has_group('event.group_event_user'),
            # environment
            'hostname': request.httprequest.host.split(':')[0],
            'is_event_user': request.env.user.has_group('event.group_event_registration_desk'),
        }

    # ------------------------------------------------------------
    # BUSINESS / MISC
    # ------------------------------------------------------------

    @http.route('/event_sponsor/<int:sponsor_id>/read', type='json', auth='public', website=True)
    def event_sponsor_read(self, sponsor_id):
        """ Marshmalling data for "event not started / sponsor not available" modal """
        sponsor = request.env['event.sponsor'].browse(sponsor_id)
        sponsor_data = sponsor.read([
            'name', 'subtitle',
            'url', 'email', 'phone',
            'website_description', 'website_image_url',
            'hour_from', 'hour_to', 'is_in_opening_hours',
            'event_date_tz', 'country_flag_url',
        ])[0]
        if sponsor.country_id:
            sponsor_data['country_name'] = sponsor.country_id.name
            sponsor_data['country_id'] = sponsor.country_id.id
        else:
            sponsor_data['country_name'] = False
            sponsor_data['country_id'] = False
        if sponsor.sponsor_type_id:
            sponsor_data['sponsor_type_name'] = sponsor.sponsor_type_id.name
            sponsor_data['sponsor_type_id'] = sponsor.sponsor_type_id.id
        else:
            sponsor_data['sponsor_type_name'] = False
            sponsor_data['sponsor_type_id'] = False
        sponsor_data['event_name'] = sponsor.event_id.name
        sponsor_data['event_is_ongoing'] = sponsor.event_id.is_ongoing
        sponsor_data['event_is_done'] = sponsor.event_id.is_done
        sponsor_data['event_start_today'] = sponsor.event_id.start_today
        sponsor_data['event_start_remaining'] = sponsor.event_id.start_remaining
        sponsor_data['event_date_begin_located'] = sponsor.event_id.date_begin_located
        sponsor_data['event_date_end_located'] = sponsor.event_id.date_end_located
        sponsor_data['hour_from_str'] = format_duration(sponsor_data['hour_from'])
        sponsor_data['hour_to_str'] = format_duration(sponsor_data['hour_to'])

        return sponsor_data

