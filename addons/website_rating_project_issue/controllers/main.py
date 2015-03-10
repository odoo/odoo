# -*- coding: utf-8 -*-
from openerp import _
from openerp.addons.web import http
from openerp.addons.web.http import request

import datetime

class WebsiteRatingProject(http.Controller):

    @http.route(['/project/rating/'], type='http', auth="public", website=True)
    def index(self, **kw):
        projects = request.env['project.project'].search([('is_visible_happy_customer', '=', 1)])
        values = {'projects' : projects}
        return request.website.render('website_rating_project_issue.index', values)

    @http.route(['''/project/rating/<model("project.project", "[('is_visible_happy_customer','=',1)]"):project>'''], type='http', auth="public", website=True)
    def page(self, project=None, **kw):
        # create domain for rating
        issues = request.env['project.issue'].search([('project_id', '=', project.id)])
        domain = [('res_model', '=', 'project.issue'), ('res_id', 'in', issues.ids)]
        ratings = request.env['rating.rating'].search(domain, order="id desc", limit=100)

        yesterday = (datetime.date.today()-datetime.timedelta(days=-1)).strftime('%Y-%m-%d 23:59:59')
        stats = {}
        for x in (7, 30, 90):
            todate = (datetime.date.today()-datetime.timedelta(days=x)).strftime('%Y-%m-%d 00:00:00')
            domdate = domain + [('create_date', '<=', yesterday), ('create_date', '>=', todate)]
            stats[x] = {0: 0, 5: 0, 10: 0}
            rating_stats = request.env['rating.rating'].read_group(domdate, [], ['rating'])
            total = reduce(lambda x, y: y['rating_count']+x, rating_stats, 0)
            for rate in rating_stats:
                stats[x][rate['rating']] = (rate['rating_count'] * 100) / total
        values = {
            'team': project.sudo().members,
            'project': project,
            'ratings' : ratings,
            'stats': stats,
        }
        return request.website.render('website_rating_project_issue.project_rating_page', values)
