# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class WebsiteRatingProject(http.Controller):

    @http.route(['/project/rating/'], type='http', auth="public", website=True)
    def index(self, **kw):
        projects = request.env['project.project'].sudo().search([('rating_status', '!=', 'no'), ('website_published', '=', True)])
        values = {'projects': projects}
        return request.render('website_rating_project_issue.index', values)

    @http.route(['/project/rating/<int:project_id>'], type='http', auth="public", website=True)
    def page(self, project_id=None, **kw):
        user = request.env.user
        project = request.env['project.project'].sudo().browse(project_id)
        # to avoid giving any access rights on projects to the public user, let's use sudo
        # and check if the user should be able to view the project (project managers only if it's unpublished or has no rating)
        if not ((project.rating_status!='no') and project.website_published) and not user.sudo(user).has_group('project.group_project_manager'):
            raise NotFound()
        values = {
            'project': project,
            'partner_task_rating': request.env['project.rating']._get_partner_rating("project_task", "project.task", project_id, limit=50),
            'partner_issue_rating': request.env['project.rating']._get_partner_rating("project_issue", "project.issue", project_id, limit=50),
        }
        return request.render('website_rating_project_issue.project_rating_page', values)
