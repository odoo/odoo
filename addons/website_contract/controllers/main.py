# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request

class website_project(http.Controller):

    @http.route(['/projects/'], type='http', auth="public")
    def blog(self, **post):
        website = request.registry['website']
        return website.render("website_project.index", values)
