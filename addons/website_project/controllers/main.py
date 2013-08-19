# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request

class website_project(http.Controller):

    @http.route(['/projects/'], type='http', auth="public")
    def blog(self, **post):
        website = request.registry['website']
        project_obj = request.registry['project.project']
        project_ids = project_obj.search(request.cr, request.uid, [('privacy_visibility', "=", "public")])
        values = website.get_rendering_context({
            'project_ids': project_obj.browse(request.cr, request.uid, project_ids)
        })
        return website.render("website_project.index", values)
