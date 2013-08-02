# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website import website

class website_hr(http.Controller):

    @http.route(['/hr'], type='http', auth="public")
    def blog(self, **post):
        hr_obj = request.registry['hr.employee']

        employee_ids = hr_obj.search(request.cr, request.uid, [(1, "=", 1)])
        values = {
            'employee_ids': hr_obj.browse(request.cr, request.uid, employee_ids),
        }

        html = website.render("website_hr.index", values)
        return html

    @http.route(['/hr/publish'], type='http', auth="public")
    def publish(self, **post):
        obj_id = int(post['id'])
        data_obj = request.registry['hr.employee']

        obj = data_obj.browse(request.cr, request.uid, obj_id)
        data_obj.write(request.cr, request.uid, [obj_id], {'website_published': not obj.website_published})
        obj = data_obj.browse(request.cr, request.uid, obj_id)

        return obj.website_published and "1" or "0"

    @http.route(['/hr/publish_contact'], type='http', auth="public")
    def publish_contact(self, **post):
        obj_id = int(post['id'])
        data_obj = request.registry['hr.employee']

        obj = data_obj.browse(request.cr, request.uid, obj_id)
        data_obj.write(request.cr, request.uid, [obj_id], {'website_published_on_contact_form': not obj.website_published_on_contact_form})
        obj = data_obj.browse(request.cr, request.uid, obj_id)

        return obj.website_published_on_contact_form and "1" or "0"
