# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from werkzeug.exceptions import NotFound

from odoo import fields
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.website_google_map.controllers.main import GoogleMap
from odoo.addons.website_partner.controllers.main import WebsitePartnerPage

from odoo.tools.translate import _


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
                    ('is_won', '!=', True), '|', ('team_id', '=', False), ('team_id', '=', opp.team_id.id)
                ], order='sequence desc, name desc, id desc'),
                'activity_types': request.env['mail.activity.type'].sudo().search(['|', ('res_model', '=', opp._name), ('res_model', '=', False)]),
                'states': request.env['res.country.state'].sudo().search([]),
                'countries': request.env['res.country'].sudo().search([]),
            })
