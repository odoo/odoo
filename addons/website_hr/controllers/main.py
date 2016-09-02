# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

class WebsiteHr(http.Controller):

    @http.route(['/page/website.aboutus', '/page/aboutus'], type='http', auth="public", website=True)
    def blog(self, **post):
        employees_domain = []
        if not request.env['res.users'].has_group('website.group_website_publisher'):
            employees_domain += [('website_published', '=', True)]
        employees = request.env['hr.employee'].search(employees_domain)
        return request.render("website.aboutus", {'employees': employees})
