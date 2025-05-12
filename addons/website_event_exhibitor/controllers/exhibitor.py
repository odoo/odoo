# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from collections import OrderedDict
from random import randint, sample
from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.addons.website_event.controllers.main import WebsiteEventController
from odoo.fields import Domain
from odoo.http import request
from odoo.tools import format_duration


class ExhibitorController(WebsiteEventController):

    def _get_event_sponsors_base_domain(self, event):
        search_domain_base = [
            ('event_id', '=', event.id),
            ('exhibitor_type', 'in', ['exhibitor', 'online']),
        ]
        if not request.env.user.has_group('event.group_event_registration_desk'):
            search_domain_base = Domain.AND([search_domain_base, [('is_published', '=', True)]])
        return search_domain_base

    # ------------------------------------------------------------
    # MAIN PAGE
    # ------------------------------------------------------------

    @http.route([
        # TDE BACKWARD: exhibitors is actually a typo
        '/event/<model("event.event"):event>/exhibitors',
        # TDE BACKWARD: matches event/event-1/exhibitor/exhib-1 sub domain
        '/event/<model("event.event"):event>/exhibitor'
    ], type='http', auth="public", website=True, sitemap=False, methods=['GET', 'POST'])
    def event_exhibitors(self, event, **searches):
        return request.render(
            "website_event_exhibitor.event_exhibitors",
            self._event_exhibitors_get_values(event, **searches) | {'seo_object': event.exhibitor_menu_ids}
        )

    def _event_exhibitors_get_values(self, event, **searches):
        # init and process search terms
        searches.setdefault('search', '')
        searches.setdefault('countries', '')
        searches.setdefault('sponsorships', '')
        search_domain_base = self._get_event_sponsors_base_domain(event)
        search_domain = search_domain_base

        # search on content
        if searches.get('search'):
            search_domain = Domain.AND([
                search_domain,
                ['|', ('name', 'ilike', searches['search']), ('website_description', 'ilike', searches['search'])]
            ])

        # search on countries
        search_countries = self._get_search_countries(searches['countries'])
        if search_countries:
            search_domain = Domain.AND([
                search_domain,
                [('partner_id.country_id', 'in', search_countries.ids)]
            ])

        # search on sponsor types
        search_sponsorships = self._get_search_sponsorships(searches['sponsorships'])
        if search_sponsorships:
            search_domain = Domain.AND([
                search_domain,
                [('sponsor_type_id', 'in', search_sponsorships.ids)]
            ])

        # fetch data to display; use sudo to allow reading partner info, be sure domain is correct
        event = event.with_context(tz=event.date_tz or 'UTC')
        sorted_sponsors = request.env['event.sponsor'].sudo().search(
            search_domain
        ).sorted(lambda sponsor: (sponsor.sponsor_type_id.sequence, sponsor.sequence))
        sponsors_all = request.env['event.sponsor'].sudo().search(search_domain_base)
        sponsor_types = sponsors_all.mapped('sponsor_type_id')
        sponsor_countries = sponsors_all.mapped('partner_id.country_id').sorted('name')
        # organize sponsors into categories to help display
        sponsor_categories_dict = OrderedDict()
        sponsor_categories = []
        is_event_user = request.env.user.has_group('event.group_event_registration_desk')
        for sponsor in sorted_sponsors:
            if not sponsor_categories_dict.get(sponsor.sponsor_type_id):
                sponsor_categories_dict[sponsor.sponsor_type_id] = request.env['event.sponsor'].sudo()
            sponsor_categories_dict[sponsor.sponsor_type_id] |= sponsor

        for sponsor_category, sponsors in sponsor_categories_dict.items():
            # To display random published sponsors first and random unpublished sponsors last
            if is_event_user:
                published_sponsors = sponsors.filtered(lambda s: s.website_published)
                unpublished_sponsors = sponsors - published_sponsors
                random_sponsors = sample(published_sponsors, len(published_sponsors)) + sample(unpublished_sponsors, len(unpublished_sponsors))
            else:
                random_sponsors = sample(sponsors, len(sponsors))
            sponsor_categories.append({
                'sponsorship': sponsor_category,
                'sponsors': random_sponsors,
            })

        # return rendering values
        return {
            # event information
            'event': event,
            'main_object': event,
            'sponsor_categories': sponsor_categories,
            'hide_sponsors': True,
            # search information
            'searches': searches,
            'search_count': len(sorted_sponsors),
            'search_key': searches['search'],
            'search_countries': search_countries,
            'search_sponsorships': search_sponsorships,
            'sponsor_types': sponsor_types,
            'sponsor_countries': sponsor_countries,
            # environment
            'hostname': request.httprequest.host.split(':')[0],
            'is_event_user': is_event_user,
        }

    # ------------------------------------------------------------
    # FRONTEND FORM
    # ------------------------------------------------------------

    @http.route(['''/event/<model("event.event", "[('exhibitor_menu', '=', True)]"):event>/exhibitor/<model("event.sponsor", "[('event_id', '=', event.id)]"):sponsor>'''],
                type='http', auth="public", website=True, sitemap=True)
    def event_exhibitor(self, event, sponsor, **options):
        if not sponsor.has_access('read'):
            raise Forbidden()
        sponsor = sponsor.sudo()

        return request.render(
            "website_event_exhibitor.event_exhibitor_main",
            self._event_exhibitor_get_values(event, sponsor, **options)
        )

    def _event_exhibitor_get_values(self, event, sponsor, **options):
        # search for exhibitor list
        search_domain_base = self._get_event_sponsors_base_domain(event)
        search_domain_base = Domain.AND([
            search_domain_base,
            [('id', '!=', sponsor.id)]
        ])
        sponsors_other = request.env['event.sponsor'].sudo().search(search_domain_base)
        current_country = sponsor.partner_id.country_id

        sponsors_other = sponsors_other.sorted(key=lambda sponsor: (
            sponsor.website_published,
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
            'website_visitor_timezone': request.env['website.visitor']._get_visitor_timezone(),
        }

    # ------------------------------------------------------------
    # BUSINESS / MISC
    # ------------------------------------------------------------

    @http.route('/event_sponsor/<int:sponsor_id>/read', type='jsonrpc', auth='public', website=True)
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
        # needs sudo access as public users can't read the model
        sponsor_type_sudo = sponsor.sponsor_type_id.sudo()
        sponsor_data['sponsor_type_name'] = sponsor_type_sudo.name
        sponsor_data['sponsor_type_id'] = sponsor_type_sudo.id
        sponsor_data['event_name'] = sponsor.event_id.name
        sponsor_data['event_is_ongoing'] = sponsor.event_id.is_ongoing
        sponsor_data['event_is_done'] = sponsor.event_id.is_done
        sponsor_data['event_start_today'] = sponsor.event_id.start_today
        sponsor_data['event_start_remaining'] = sponsor.event_id.start_remaining
        sponsor_data['event_date_begin'] = sponsor.event_id.date_begin
        sponsor_data['hour_from_str'] = format_duration(sponsor_data['hour_from'])
        sponsor_data['hour_to_str'] = format_duration(sponsor_data['hour_to'])

        return sponsor_data

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _get_search_countries(self, country_search):
        # TDE FIXME: make me generic (slides, event, ...)
        country_ids = set(request.httprequest.form.getlist('sponsor_country'))
        try:
            country_ids.update(literal_eval(country_search))
        except Exception:
            pass
        # perform a search to filter on existing / valid tags implicitly
        return request.env['res.country'].sudo().search([('id', 'in', list(country_ids))])

    def _get_search_sponsorships(self, sponsorship_search):
        # TDE FIXME: make me generic (slides, event, ...)
        sponsorship_ids = set(request.httprequest.form.getlist('sponsor_type'))
        try:
            sponsorship_ids.update(literal_eval(sponsorship_search))
        except Exception:
            pass
        # perform a search to filter on existing / valid tags implicitly
        return request.env['event.sponsor.type'].sudo().search([('id', 'in', list(sponsorship_ids))])
