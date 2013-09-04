# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website import website


class Website(osv.osv):
    _inherit = "website"
    def get_webcontext(self, values={}, **kw):
        project_obj = request.registry['project.project']
        project_ids = project_obj.search(request.cr, request.uid, [('privacy_visibility', "=", "public")])
        values.update({
            'project_ids': project_obj.browse(request.cr, request.uid, project_ids),
        })
        return super(Website, self).get_webcontext(values, **kw)


class website_project(http.Controller):

    @website.route(['/project/<int:project_id>/'], type='http', auth="public")
    def blog(self, project_id=None, **post):
        project_obj = request.registry['project.project']
        project = project_obj.browse(request.cr, request.uid, project_id)
        return request.webcontext.render("website_project.index", {'project_id': project})
