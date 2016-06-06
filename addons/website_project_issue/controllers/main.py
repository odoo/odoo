# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from openerp import http, _
from openerp.addons.website_portal.controllers.main import website_account
from openerp.http import request


class WebsiteAccount(website_account):

    @http.route()
    def account(self):
        response = super(WebsiteAccount, self).account()
        # TDE FIXME: shouldn't that be mnaged by the access rule itself ?
        # portal projects where you or someone from your company are a follower
        user = request.env.user
        issue_count = request.env['project.issue'].sudo().search_count([
            '&',
            ('project_id.privacy_visibility', '=', 'portal'),
            ('message_partner_ids', 'child_of', [user.partner_id.commercial_partner_id.id, user.partner_id.id])
        ])
        response.qcontext.update({'issue_count': issue_count})
        return response

    @http.route(['/my/issues', '/my/issues/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_issues(self, page=1, date_begin=None, date_end=None, project=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        ProjectIssue = request.env['project.issue']
        domain = []

        sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc'},
        }

        projects = request.env['project.project'].search([])

        project_filters = {
            'all': {'label': _('All'), 'domain': []},
        }

        for proj in projects:
            project_filters.update({
                str(proj.id): {'label': proj.name, 'domain': [('project_id', '=', proj.id)]}
            })

        domain += project_filters.get(project, project_filters['all'])['domain']
        order = sortings.get(sortby, sortings['date'])['order']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('project.issue', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        # pager
        issue_count = ProjectIssue.search_count(domain)
        pager = request.website.pager(
            url="/my/issues",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=issue_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        project_issues = ProjectIssue.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

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
        return request.website.render("website_project_issue.portal_my_issues", values)

    @http.route(['/my/issues/<int:issue_id>'], type='http', auth="user", website=True)
    def issues_followup(self, issue_id=None, **kw):
        issue = request.env['project.issue'].browse(issue_id)
        return request.website.render("website_project_issue.issues_followup", {'issue': issue})
