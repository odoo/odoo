# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import http
from openerp.addons.website_portal.controllers.main import website_account
from openerp.http import request


class WebsiteAccount(website_account):

    @http.route()
    def account(self):
        response = super(WebsiteAccount, self).account()
        issue_count = request.env['project.issue'].search_count([])
        response.qcontext.update({'issue_count': issue_count})
        return response

    @http.route(['/my/issues', '/my/issues/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_issues(self, page=1, date_begin=None, date_end=None, **kw):
        values = self._prepare_portal_layout_values()
        ProjectIssue = request.env['project.issue']
        domain = []
        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('project.issue', domain)
        if date_begin and date_end:
            domain += [('create_date', '>=', date_begin), ('create_date', '<', date_end)]
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
        project_issues = ProjectIssue.search(domain, order="stage_id", limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
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
