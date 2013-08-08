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

    @http.route(['/page/website.aboutus/publish'], type='http', auth="public")
    def publish(self, **post):
        obj_id = int(post['id'])
        data_obj = request.registry['hr.employee']

        obj = data_obj.browse(request.cr, request.uid, obj_id)
        data_obj.write(request.cr, request.uid, [obj_id], {'website_published': not obj.website_published})
        obj = data_obj.browse(request.cr, request.uid, obj_id)

        return obj.website_published and "1" or "0"