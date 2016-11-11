# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import http, _
from odoo.addons.website_portal.controllers.main import website_account
from odoo.http import request


class WebsiteAccount(website_account):

    def _prepare_portal_layout_values(self):
        values = super(WebsiteAccount, self)._prepare_portal_layout_values()
        # domain is needed to hide non portal project for employee
        # portal users can't see the privacy_visibility, fetch the domain for them in sudo
        portal_projects = request.env['project.project'].sudo().search([('privacy_visibility', '=', 'portal')])
        issue_count = request.env['project.issue'].search_count([('project_id', 'in', portal_projects.ids)])
        values.update({
            'issue_count': issue_count,
        })
        return values

    @http.route(['/my/issues', '/my/issues/page/<int:page>'], type='http', auth="user", website=True)
    def my_issues(self, page=1, date_begin=None, date_end=None, project=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()

        sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc'},
        }

        projects = request.env['project.project'].search([('privacy_visibility','=','portal')])

        project_filters = {
            'all': {'label': _('All'), 'domain': []},
        }

        for proj in projects:
            project_filters.update({
                str(proj.id): {'label': proj.name, 'domain': [('project_id', '=', proj.id)]}
            })

        # portal users can't see the privacy_visibility, fetch the domain for them in sudo
        portal_projects = request.env['project.project'].sudo().search([('privacy_visibility', '=', 'portal')])
        domain = [('project_id', 'in', portal_projects.ids)]
        domain += project_filters.get(project, project_filters['all'])['domain']
        order = sortings.get(sortby, sortings['date'])['order']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('project.issue', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        # pager
        pager = request.website.pager(
            url="/my/issues",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=values['issue_count'],
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        project_issues = request.env['project.issue'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'project_filters': OrderedDict(sorted(project_filters.items())),
            'projects': projects,
            'project': project,
            'sortings': sortings,
            'sortby': sortby,
            'issues': project_issues,
            'page_name': 'issue',
            'archive_groups': archive_groups,
            'default_url': '/my/issues',
            'pager': pager
        })
        return request.render("website_project_issue.my_issues", values)

    @http.route(['/my/issues/<int:issue_id>'], type='http', auth="user", website=True)
    def my_issues_issue(self, issue_id=None, **kw):
        issue = request.env['project.issue'].browse(issue_id)
        return request.render("website_project_issue.my_issues_issue", {'issue': issue})
