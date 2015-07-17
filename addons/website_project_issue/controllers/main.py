# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import werkzeug

from openerp import http
from openerp.http import request

from openerp.addons.website_portal.controllers.main import website_account

class WebsiteAccount(website_account):
    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def account(self):
        response = super(WebsiteAccount, self).account()
        #searching issues of related to logged in user as sudo to by-pass existing record rules
        project_issues = request.env['project.issue'].sudo().search([('partner_id', '=', request.env.user.partner_id.id)])
        response.qcontext.update({
            'issues': project_issues
        })
        return response

class website_project_issues(http.Controller):
    @http.route(['/my/issues/<int:issue_id>'], type='http', auth="user", website=True)
    def issues_followup(self, issue_id=None):
        note_subtype_id = request.env.ref('mail.mt_note').id
        #accessing recordset as sudo to by-pass existing record rules. Chatter messages needs to be filtered
        #to not display internal notes as existing record-rule for internal notes won't apply cause of sudo.
        issue = request.env['project.issue'].sudo().browse(issue_id)
        has_timesheet_enabled = issue._fields.get('timesheet_ids')
        return request.website.render("website_project_issue.issues_followup", {
            'issue': issue,
            'has_timesheet_enabled': has_timesheet_enabled,
            'messages': issue.message_ids.filtered(lambda message: message.subtype_id.id != note_subtype_id)
        })

    @http.route(['/issue/<int:issue_id>/post'], type='http', auth="user", website=True)
    def post(self, issue_id=None, **post):
        message = post.get('comment')
        #accessing recordset as sudo to by-pass existing record rules
        if message :
            issue = request.env['project.issue'].browse(issue_id)
            issue.sudo().message_post(
                body=message,
                message_type='comment',
                subtype='mt_comment',
                author_id=request.env.user.partner_id.id
            )
        return werkzeug.utils.redirect(request.httprequest.referrer + "#comment")
