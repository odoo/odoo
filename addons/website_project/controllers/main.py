# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website import website


class Website(osv.osv):
    _inherit = "website"
    def preprocess_request(self, cr, uid, ids, *args, **kwargs):
        project_obj = request.registry['project.project']
        project_ids = project_obj.search(cr, uid, [('privacy_visibility', "=", "public")], context=request.context)

        # FIXME: namespace global rendering vars
        request.context['project_ids'] = project_obj.browse(cr, uid, project_ids, request.context)

        return super(Website, self).preprocess_request(cr, uid, ids, *args, **kwargs)


class website_project(http.Controller):

    @website.route(['/project/<int:project_id>/'], type='http', auth="public")
    def blog(self, project_id=None, **post):
        project_obj = request.registry['project.project']
        project = project_obj.browse(request.cr, request.uid, project_id, request.context)
        return request.website.render("website_project.index", {'project_id': project})
