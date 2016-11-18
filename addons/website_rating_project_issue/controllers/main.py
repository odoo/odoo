# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

import base64
import werkzeug.exceptions
import werkzeug.urls
import werkzeug.wrappers
import datetime

from odoo import http, modules, SUPERUSER_ID
from odoo.http import request
from odoo.addons.web.controllers.main import binary_content


class WebsiteRatingProject(http.Controller):

    @http.route(['/project/rating/'], type='http', auth="public", website=True)
    def index(self, **kw):
        projects = request.env['project.project'].sudo().search([('rating_status', '!=', 'no'), ('website_published', '=', True)])
        values = {'projects': projects}
        return request.render('website_rating_project_issue.index', values)

    @http.route(['/rating/partner/<int:rated_partner_id>/avatar'], type='http', auth="public")
    def user_image(self, rated_partner_id=0, **post):
        status, headers, content = binary_content(model='res.partner', id=rated_partner_id, field='image_small', default_mimetype='image/png', env=request.env(user=SUPERUSER_ID))

        if not content:
            img_path = modules.get_module_resource('web', 'static/src/img', 'placeholder.png')
            with open(img_path, 'rb') as f:
                image = f.read()
            content = image.encode('base64')
        if status == 304:
            return werkzeug.wrappers.Response(status=304)
        image_base64 = base64.b64decode(content)
        headers.append(('Content-Length', len(image_base64)))
        response = request.make_response(image_base64, headers)
        response.status = str(status)
        return response

    @http.route(['/project/rating/<int:project_id>'], type='http', auth="public", website=True)
    def page(self, project_id=None, **kw):
        user = request.env.user
        project = request.env['project.project'].sudo().browse(project_id)
        # to avoid giving any access rights on projects to the public user, let's use sudo
        # and check if the user should be able to view the project (project managers only if it's unpublished or has no rating)
        if not ((project.rating_status<>'no') and project.website_published) and not user.sudo(user).has_group('project.group_project_manager'):
            raise NotFound()
        values = {
            'project': project,
            'task_data': self._calculate_rating(project.id, "project.task"),
            'issue_data': self._calculate_rating(project.id, "project.issue"),
            'top_rated_partner_task': request.env['project.task']._get_top_five_rated_partners_task(project_id),
            'top_rated_partner_issue': request.env['project.issue']._get_top_five_rated_partners_issue(project_id),
        }
        return request.render('website_rating_project_issue.project_rating_page', values)

    def _calculate_rating(self, project_id, model_name):
        # Calculate rating for Tasks and Issues
        records = request.env[model_name].sudo().search([('project_id', '=', project_id)])
        domain = [('res_model', '=', model_name), ('res_id', 'in', records.ids), ('consumed', '=', True)]
        ratings = request.env['rating.rating'].search(domain, order="id desc", limit=100)

        today = (datetime.date.today()).strftime('%Y-%m-%d 23:59:59')
        stats = {}
        for x in (7, 30, 90):
            todate = (datetime.date.today() - datetime.timedelta(days=x)).strftime('%Y-%m-%d 00:00:00')
            domdate = domain + [('create_date', '<=', today), ('create_date', '>=', todate)]
            stats[x] = {1: 0, 5: 0, 10: 0}
            rating_stats = request.env['rating.rating'].read_group(domdate, [], ['rating'])
            total = reduce(lambda x, y: y['rating_count'] + x, rating_stats, 0)
            for rate in rating_stats:
                stats[x][rate['rating']] = float("%.2f" % (rate['rating_count'] * 100.0 / total))
        return {'ratings': ratings, 'stats': stats}
