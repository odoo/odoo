# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

import datetime

from odoo import http
from odoo.http import request


class WebsiteRatingProject(http.Controller):

    @http.route(['/project/rating/'], type='http', auth="public", website=True)
    def index(self, **kw):
        projects = request.env['project.project'].sudo().search([('rating_status', '!=', 'no'), ('portal_show_rating', '=', True)])
        values = {'projects': projects}
        return request.render('website_rating_project.index', values)

    @http.route(['/project/rating/<int:project_id>'], type='http', auth="public", website=True)
    def page(self, project_id=None, **kw):
        user = request.env.user
        project = request.env['project.project'].sudo().browse(project_id)
        # to avoid giving any access rights on projects to the public user, let's use sudo
        # and check if the user should be able to view the project (project managers only if it's unpublished or has no rating)
        if not ((project.rating_status!='no') and project.portal_show_rating) and not user.sudo(user).has_group('project.group_project_manager'):
            raise NotFound()
        values = {
            'project': project,
            'task_data': self._calculate_rating(project.id),
        }
        return request.render('website_rating_project.project_rating_page', values)

    def _calculate_rating(self, project_id):
        # Calculate rating for Tasks
        records = request.env["project.task"].sudo().search([('project_id', '=', project_id)])
        domain = [('res_model', '=', "project.task"), ('res_id', 'in', records.ids), ('consumed', '=', True)]
        ratings = request.env['rating.rating'].search(domain, order="id desc", limit=100)

        yesterday = (datetime.date.today() - datetime.timedelta(days=-1)).strftime('%Y-%m-%d 23:59:59')
        stats = {}
        for x in (7, 30, 90):
            todate = (datetime.date.today() - datetime.timedelta(days=x)).strftime('%Y-%m-%d 00:00:00')
            domdate = domain + [('create_date', '<=', yesterday), ('create_date', '>=', todate)]
            stats[x] = {1: 0, 5: 0, 10: 0}
            rating_stats = request.env['rating.rating'].read_group(domdate, [], ['rating'])
            total = sum(st['rating_count'] for st in rating_stats)
            for rate in rating_stats:
                stats[x][rate['rating']] = float("%.2f" % (rate['rating_count'] * 100.0 / total))
        return {'ratings': ratings, 'stats': stats}
