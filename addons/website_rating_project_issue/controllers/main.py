# -*- coding: utf-8 -*-
from openerp import _
from openerp.addons.web import http
from openerp.addons.web.http import request


class WebsiteRatingProject(http.Controller):

    @http.route(['/project/rating/'], type='http', auth="public", website=True)
    def index(self, **kw):
        projects = request.env['project.project'].search([])
        values = {'projects' : projects}
        return request.website.render('website_rating_project_issue.index', values)

    @http.route(['/project/rating/<model("project.project"):project>'], type='http', auth="public", website=True)
    def page(self, project=None, **kw):
        # create domain for rating
        domain = []
        if project.use_tasks:
            task_ids = [t.id for t in project.tasks]
            domain += ['&', ('res_model', '=', 'project.task'), ('res_id', 'in', task_ids)]
        if project.use_issues:
            issue_ids = [i.id for i in project.issue_ids]
            domain += ['&', ('res_model', '=', 'project.issue'), ('res_id', 'in', issue_ids)]
        if project.use_issues and project.use_tasks:
            domain = ['|'] + domain
        ratings = request.env['rating.rating'].search(domain, order="write_date desc", limit=100)
        # compute stat only for the last 100 ratings
        grades_label = {
            'success' : _('Happy'),
            'warning': _('Okay'),
            'danger': _('Bad'),
        }
        res = dict.fromkeys(grades_label.keys(), 0)
        for rating in ratings:
            if rating.rating >= 7:
                res['success'] += 1
            elif rating.rating > 3:
                res['warning'] += 1
            else:
                res['danger'] += 1
        for key, value in res.iteritems():
            res[key] = value / float(len(ratings)) * 100 if len(ratings) else 0
        # prepare and render
        values = {
            'team': project.sudo().members,
            'project': project,
            'ratings' : ratings,
            'stats': res,
            'labels': grades_label,
        }
        return request.website.render('website_rating_project_issue.project_rating_page', values)
