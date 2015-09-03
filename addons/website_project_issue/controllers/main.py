# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import http
from openerp.addons.website_portal.controllers.main import website_account
from openerp.http import request


class WebsiteAccount(website_account):
    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def account(self):
        response = super(WebsiteAccount, self).account()
        user = request.env.user
        # TDE FIXME: shouldn't that be mnaged by the access rule itself ?
        # portal projects where you or someone from your company are a follower
        project_issues = request.env['project.issue'].search([
            '&',
            ('project_id.privacy_visibility', '=', 'portal'),
            '|',
            ('message_partner_ids', 'child_of', [user.partner_id.commercial_partner_id.id]),
            ('message_partner_ids', 'child_of', [user.partner_id.id])
        ])
        response.qcontext.update({'issues': project_issues})
        return response


class WebsiteProjectIssue(http.Controller):
    @http.route(['/my/issues/<int:issue_id>'], type='http', auth="user", website=True)
    def issues_followup(self, issue_id=None):
        issue = request.env['project.issue'].browse(issue_id)
        return request.website.render("website_project_issue.issues_followup", {'issue': issue})
