# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website import website

class website_hr(http.Controller):

    @website.route(['/page/website.aboutus'], type='http', auth="public", multilang=True)
    def blog(self, **post):
        hr_obj = request.registry['hr.employee']
        employee_ids = hr_obj.search(request.cr, request.uid, [('website_published', '=', True)],
                                     context=request.context)
        values = {
            'employee_ids': hr_obj.browse(request.cr, request.uid, employee_ids,
                                          request.context)
        }
        return request.website.render("website.aboutus", values)
