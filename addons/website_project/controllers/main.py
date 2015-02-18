# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request


class WebsiteProject(http.Controller):

    @http.route(['/project/<model("project.project"):project>'], type='http', auth="public", website=True)
    def project(self, project=None, **post):
        render_values = {
            'project': project,
            'main_object': project,
        }
        return request.website.render("website_project.index", render_values)
