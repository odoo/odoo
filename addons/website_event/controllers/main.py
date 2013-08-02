# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website import website

class website_hr(http.Controller):

    @http.route(['/event'], type='http', auth="public")
    def blog(self, **post):
        data_obj = request.registry['event.event']

        obj_ids = data_obj.search(request.cr, request.uid, [(1, "=", 1)])
        values = {
            'event_ids': data_obj.browse(request.cr, request.uid, obj_ids),
        }

        html = website.render("website_event.index", values)
        return html

    @http.route(['/hr/publish'], type='http', auth="public")
    def publish(self, **post):
        obj_id = int(post['id'])
        data_obj = request.registry['event.event']

        obj = data_obj.browse(request.cr, request.uid, obj_id)
        data_obj.write(request.cr, request.uid, [obj_id], {'website_published': not obj.website_published})
        obj = data_obj.browse(request.cr, request.uid, obj_id)

        return obj.website_published and "1" or "0"
