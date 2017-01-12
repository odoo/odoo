# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import http, _
from odoo.addons.website_portal.controllers.main import website_account, get_records_pager
from odoo.http import request
from odoo.osv.expression import OR


class WebsiteAccount(website_account):

    @http.route()
    def account(self, **kw):
        response = super(WebsiteAccount, self).account(**kw)
        # domain is needed to hide non portal project for employee
        # portal users can't see the privacy_visibility, fetch the domain for them in sudo
        portal_projects = request.env['project.project'].sudo().search([('privacy_visibility', '=', 'portal')])
        response.qcontext.update({
            'issue_count': request.env['project.issue'].search_count([('project_id', 'in', portal_projects.ids)])
        })
        return response

    @http.route(['/my/issues', '/my/issues/page/<int:page>'], type='http', auth="user", website=True)
    def my_issues(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='content', **kw):
        values = self._prepare_portal_layout_values()
        # portal users can't see the privacy_visibility, fetch the domain for them in sudo
        portal_projects = request.env['project.project'].sudo().search([('privacy_visibility', '=', 'portal')])
        domain = [('project_id', 'in', portal_projects.ids)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        # extends filterby criteria with project (criteria name is the project id)
        projects = request.env['project.project'].search([('privacy_visibility', '=', 'portal')])
        for proj in projects:
            searchbar_filters.update({
                str(proj.id): {'label': proj.name, 'domain': [('project_id', '=', proj.id)]}
            })

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('project.issue', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
            if search_in in ('customer', 'all'):
                search_domain = OR([search_domain, [('partner_id', 'ilike', search)]])
            if search_in in ('message', 'all'):
                search_domain = OR([search_domain, [('message_ids.body', 'ilike', search)]])
            domain += search_domain

        # issue count
        issue_count = request.env['project.issue'].search_count(domain)
        # pager
        pager = request.website.pager(
            url="/my/issues",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=issue_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        project_issues = request.env['project.issue'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_issues_history'] = project_issues.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'projects': projects,
            'issues': project_issues,
            'page_name': 'issue',
            'archive_groups': archive_groups,
            'default_url': '/my/issues',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'search_in': search_in,
            'search': search,
        })
        return request.render("website_project_issue.my_issues", values)

    @http.route(['/my/issues/<int:issue_id>'], type='http', auth="user", website=True)
    def my_issues_issue(self, issue_id=None, **kw):
        issue = request.env['project.issue'].browse(issue_id)
        vals = {'issue': issue}
        history = request.session.get('my_issues_history', [])
        vals.update(get_records_pager(history, issue))
        return request.render("website_project_issue.my_issues_issue", vals)
