# -*- coding: utf-8 -*-

# from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request


class WebsiteEmailDesigner(http.Controller):

    @http.route('/website_mail/email_designer', type='http', auth="user", website=True, multilang=True)
    def index(self, model=None, res_id=None, **kw):
        if not model or not model in request.registry or not res_id:
            return request.redirect('/')
        if not 'body' in request.registry[model]._all_columns and not 'body_html' in request.registry[model]._all_columns:
            return request.redirect('/')
        obj_ids = request.registry[model].exists(request.cr, request.uid, [res_id], context=request.context)
        if not obj_ids:
            return request.redirect('/')
        values = {
            'object': request.registry[model].browse(request.cr, request.uid, obj_ids[0], context=request.context),
            'model': request.registry[model],
            'model_name': model,
            'res_id': res_id,
        }
        return request.website.render("website_mail.designer_index", values)

    @http.route(['/website_mail/snippets'], type='json', auth="user", website=True)
    def snippets(self):
        return request.website._render('website_mail.email_designer_snippets')
