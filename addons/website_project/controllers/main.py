# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.addons.web import http
from openerp.addons.web.http import request


class website(osv.osv):
    _inherit = "website"
    def get_rendering_context(self, additional_values=None, **kw):
        project_obj = request.registry['project.project']
        project_ids = project_obj.search(request.cr, request.uid, [('privacy_visibility', "=", "public")])
        values = {
            'project_ids': project_obj.browse(request.cr, request.uid, project_ids),
        }
        if additional_values:
            values.update(additional_values)
        return super(website, self).get_rendering_context(values)


class website_project(http.Controller):

    @http.route(['/project/<int:project_id>/'], type='http', auth="public")
    def blog(self, project_id=None, **post):
        website = request.registry['website']
        project_obj = request.registry['project.project']

        project = project_obj.browse(request.cr, request.uid, project_id)

        values = website.get_rendering_context({
            'project_id': project,
        })
        return website.render("website_project.index", values)
