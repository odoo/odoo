# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from werkzeug.exceptions import NotFound

from odoo import fields
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.website_google_map.controllers.main import GoogleMap
from odoo.addons.website_partnership.controllers.main import WebsitePartnership
from odoo.fields import Domain

from odoo.tools.translate import _, LazyTranslate

_lt = LazyTranslate(__name__)


class WebsiteAccount(CustomerPortal):

    def get_domain_my_lead(self, user):
        return [
            ('partner_assigned_id', 'child_of', user.commercial_partner_id.id),
            ('type', '=', 'lead')
        ]

    def get_domain_my_opp(self, user):
        return [
            ('partner_assigned_id', 'child_of', user.commercial_partner_id.id),
            ('type', '=', 'opportunity')
        ]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        CrmLead = request.env['crm.lead']
        if 'lead_count' in counters:
            values['lead_count'] = (
                CrmLead.search_count(self.get_domain_my_lead(request.env.user))
                if CrmLead.has_access('read')
                else 0
            )
        if 'opp_count' in counters:
            values['opp_count'] = (
                CrmLead.search_count(self.get_domain_my_opp(request.env.user))
                if CrmLead.has_access('read')
                else 0
            )
        return values

    @http.route(['/my/leads', '/my/leads/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_leads(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        CrmLead = request.env['crm.lead']
        domain = self.get_domain_my_lead(request.env.user)

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'contact_name': {'label': _('Contact Name'), 'order': 'contact_name'},
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # pager
        lead_count = CrmLead.search_count(domain)
        pager = request.website.pager(
            url="/my/leads",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=lead_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        leads = CrmLead.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'leads': leads,
            'page_name': 'lead',
            'default_url': '/my/leads',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("website_crm_partner_assign.portal_my_leads", values)

    @http.route(['/my/opportunities', '/my/opportunities/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_opportunities(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        CrmLead = request.env['crm.lead']
        domain = self.get_domain_my_opp(request.env.user)

        today = fields.Date.today()

        searchbar_filters = {
            'all': {'label': _('Active'), 'domain': []},
            'no_activities': {
                'label': _('No Activities'),
                'domain': [('activity_ids', 'not any', [('user_id', '=', request.env.user.id)]), ('stage_id.is_won', '=', False)]
            },
            'overdue': {'label': _('Late Activities'), 'domain': [('activity_date_deadline', '<', today)]},
            'today': {'label': _('Today Activities'), 'domain': [('activity_date_deadline', '=', today)]},
            'future': {'label': _('Future Activities'), 'domain': [('activity_date_deadline', '>', today)]},
            'won': {'label': _('Won'), 'domain': [('won_status', '=', 'won')]},
            'lost': {'label': _('Lost'), 'domain': [('won_status', '=', 'lost')]},
        }
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'contact_name': {'label': _('Contact Name'), 'order': 'contact_name'},
            'revenue': {'label': _('Expected Revenue'), 'order': 'expected_revenue desc'},
            'probability': {'label': _('Probability'), 'order': 'probability desc'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        if filterby == 'lost':
            CrmLead = CrmLead.with_context(active_test=False)

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        # pager: bypass activities access rights for search but still apply access rules
        leads_sudo = CrmLead.sudo()._search(domain)
        domain = [('id', 'in', leads_sudo)]
        opp_count = CrmLead.search_count(domain)
        pager = request.website.pager(
            url="/my/opportunities",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=opp_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager
        opportunities = CrmLead.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'opportunities': opportunities,
            'page_name': 'opportunity',
            'default_url': '/my/opportunities',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        })
        return request.render("website_crm_partner_assign.portal_my_opportunities", values)

    @http.route(['''/my/lead/<model('crm.lead', "[('type','=', 'lead')]"):lead>'''], type='http', auth="user", website=True)
    def portal_my_lead(self, lead, **kw):
        if lead.type != 'lead':
            raise NotFound()
        return request.render("website_crm_partner_assign.portal_my_lead", {'lead': lead})

    @http.route(['''/my/opportunity/<model('crm.lead', "[('type','=', 'opportunity')]"):opp>'''], type='http', auth="user", website=True)
    def portal_my_opportunity(self, opp, **kw):
        if opp.type != 'opportunity':
            raise NotFound()

        return request.render(
            "website_crm_partner_assign.portal_my_opportunity", {
                'opportunity': opp,
                'user_activity': opp.sudo().activity_ids.filtered(lambda activity: activity.user_id == request.env.user)[:1],
                'stages': request.env['crm.stage'].search([
                    ('is_won', '!=', True), '|', ('team_ids', '=', False), ('team_ids', 'in', opp.team_id.id)
                ], order='sequence desc, name desc, id desc'),
                'activity_types': request.env['mail.activity.type'].sudo().search(['|', ('res_model', '=', opp._name), ('res_model', '=', False)]),
                'states': request.env['res.country.state'].sudo().search([]),
                'countries': request.env['res.country'].sudo().search([]),
            })


class WebsiteCrmPartnerAssign(WebsitePartnership, GoogleMap):
    _references_per_page = 40

    def _get_gmap_domains(self, **kw):
        if kw.get('dom', '') != "website_crm_partner_assign.partners":
            return super()._get_gmap_domains(**kw)
        current_grade = kw.get('current_grade')
        current_country = kw.get('current_country')

        domain = [('grade_id', '!=', False), ('is_company', '=', True)]
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            domain += [('grade_id.website_published', '=', True)]

        if current_country:
            domain += [('country_id', '=', int(current_country))]

        if current_grade:
            domain += [('grade_id', '=', int(current_grade))]

        return domain

    def sitemap_partners(env, rule, qs):
        if not qs or qs.lower() in '/partners':
            yield {'loc': '/partners'}

        slug = env['ir.http']._slug
        base_partner_domain = [
            ('grade_id', '!=', False),
            ('website_published', '=', True),
            ('grade_id.website_published', '=', True),
            ('grade_id.active', '=', True),
        ]
        grades = env['res.partner'].sudo()._read_group(base_partner_domain, groupby=['grade_id'])
        for [grade] in grades:
            loc = '/partners/grade/%s' % slug(grade)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}
        country_partner_domain = base_partner_domain + [('country_id', '!=', False)]
        countries = env['res.partner'].sudo()._read_group(country_partner_domain, groupby=['country_id'])
        for [country] in countries:
            loc = '/partners/country/%s' % slug(country)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    def _get_partners_detail_values(self, partner_id, **post):
        values = super()._get_partners_detail_values(partner_id, **post)
        if country_id := post.get('country_id'):
            values.update({'current_country': request.env['res.country'].browse(int(country_id)).exists()})
        return values

    def _get_partners_values(self, country=None, grade=None, page=0, references_per_page=20, **post):
        country_all = post.pop('country_all', False)
        partner_obj = request.env['res.partner']
        country_obj = request.env['res.country']

        industries = request.env['res.partner.industry'].sudo().search([])
        industry_param = request.env['ir.http']._unslug(post.pop('industry', ''))[1]
        current_industry = industry_param in industries.ids and industries.browse(int(industry_param))

        search = post.get('search', '')

        base_partner_domain = self._get_base_partner_domain(search, searched_fields=('name', 'website_description', 'street', 'street2', 'city', 'zip', 'state_id', 'country_id'))

        if not country and not country_all:
            if request.geoip.country_code:
                country = country_obj.search([('code', '=', request.geoip.country_code)], limit=1)
        # Group by country
        country_domain = list(base_partner_domain)
        if grade:
            country_domain += [('grade_id', '=', grade.id)]
        country_groups = partner_obj.sudo()._read_group(
            country_domain + [('country_id', '!=', False)],
            ["country_id"], ["__count"], order="country_id")

        # Fallback on all countries if no partners found for the country and
        # there are matching partners for other countries.
        fallback_all_countries = country and country.id not in (c.id for c, __ in country_groups)
        if fallback_all_countries:
            country = None

        grade_domain = list(base_partner_domain)
        if country:
            grade_domain += [('country_id', '=', country.id)]
        grades = self._get_grades(grade, grade_domain)

        # Group by country
        country_domain = list(base_partner_domain)
        if grade:
            country_domain += [('grade_id', '=', grade.id)]
        country_groups = partner_obj.sudo()._read_group(
            country_domain + [('country_id', '!=', False)],
            ["country_id"], ["__count"], order="country_id")
        countries = [{
            'country_id_count': sum(count for __, count in country_groups),
            'country_id': (0, _("All Countries")),
            'active': country is None,
        }]
        for g_country, count in country_groups:
            countries.append({
                'country_id_count': count,
                'country_id': (g_country.id, g_country.display_name),
                'active': country and g_country.id == country.id,
            })

        # current search, modify the base_partner_domain
        if request.website.is_view_active("website_partnership.categories_setting") and grade:
            base_partner_domain = Domain.AND([base_partner_domain, Domain('grade_id', '=', grade.id)])
        if request.website.is_view_active("website_crm_partner_assign.countries_setting") and country:
            base_partner_domain = Domain.AND([base_partner_domain, Domain('country_id', '=', country.id)])
        if request.website.is_view_active("website_crm_partner_assign.industries_setting") and current_industry:
            base_partner_domain = Domain.AND([base_partner_domain, Domain('implemented_partner_ids.industry_id', 'in', current_industry.id)])

        # format pager
        slug = request.env['ir.http']._slug
        url = '/partners'
        if grade:
            url += '/grade/' + slug(grade)
        if country:
            url += '/country/' + slug(country)

        url_args = {}
        if search:
            url_args['search'] = search
        if country_all:
            url_args['country_all'] = True
        if current_industry:
            url_args['industry'] = slug(current_industry)

        partner_count = partner_obj.sudo().search_count(base_partner_domain)
        pager = request.website.pager(
            url=url, total=partner_count, page=page, step=references_per_page, scope=7,
            url_args=url_args)

        google_maps_api_key = request.website.google_maps_api_key
        partners = self._get_partners(base_partner_domain, pager, references_per_page=references_per_page, search_order="grade_sequence ASC, implemented_partner_count DESC, complete_name ASC, id ASC")

        values = {
            'industries': industries,
            'current_industry': current_industry,
            'countries': countries,
            'country_all': country_all,
            'current_country': country,
            'grades': grades,
            'current_grade': grade,
            'partners': partners,
            'pager': pager,
            'searches': post,
            'search_path': "%s" % werkzeug.urls.url_encode(post),
            'search': search,
            'google_maps_api_key': google_maps_api_key,
            'fallback_all_countries': fallback_all_countries,
        }
        return values

    @http.route([
        '/partners',
        '/partners/page/<int:page>',

        '/partners/grade/<model("res.partner.grade"):grade>',
        '/partners/grade/<model("res.partner.grade"):grade>/page/<int:page>',

        '/partners/country/<model("res.country"):country>',
        '/partners/country/<model("res.country"):country>/page/<int:page>',

        '/partners/grade/<model("res.partner.grade"):grade>/country/<model("res.country"):country>',
        '/partners/grade/<model("res.partner.grade"):grade>/country/<model("res.country"):country>/page/<int:page>',
    ], type='http', sitemap=sitemap_partners)
    def partners(self, country=None, grade=None, page=0, **post):
        values = self._get_partners_values(
            country=country,
            grade=grade,
            page=page,
            references_per_page=self._references_per_page,
            **post
        )
        return request.render("website_crm_partner_assign.index", values)
