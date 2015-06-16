# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.web import http
from openerp.addons.web.http import request

class website_project(http.Controller):

    @http.route(['/project/<model("project.project"):project>'], type='http', auth="public", website=True)
    def project(self, project=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        render_values = {
            'project': project,
            'main_object': project,
        }
        return request.website.render("website_project.index", render_values)
