# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request

class website_hr(http.Controller):

    @http.route(['/page/website.aboutus'], type='http', auth="public")
    def blog(self, **post):
        website = request.registry['website']
        hr_obj = request.registry['hr.employee']
        employee_ids = hr_obj.search(request.cr, request.uid, [(1, "=", 1)])
        values = website.get_rendering_context({
            'employee_ids': hr_obj.browse(request.cr, request.uid, employee_ids)
        })
        return website.render("website.aboutus", values)
