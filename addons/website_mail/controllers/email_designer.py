# -*- coding: utf-8 -*-

# from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request


class WebsiteEmailDesigner(http.Controller):

    @http.route('/website_mail/email_designer', type='http', auth="user", website=True, multilang=True)
    def index(self, model, res_id, template_model, field_body='body', field_from='email_from', field_subject='name', **kw):
        if not model or not model in request.registry or not res_id:
            return request.redirect('/')
#        if not 'body' in request.registry[model]._all_columns and not 'body_html' in request.registry[model]._all_columns:
#            return request.redirect('/')
        obj_ids = request.registry[model].exists(request.cr, request.uid, [res_id], context=request.context)
        if not obj_ids:
            return request.redirect('/')
        cr, uid, context = request.cr, request.uid, request.context
        tmpl_obj = request.registry['email.template']
        res_id = int(res_id)

        tids = tmpl_obj.search(cr, uid, [('model','=',template_model)], context=context)
        templates = tmpl_obj.browse(cr, uid, tids, context=context)

        print templates
        values = {
            'object': request.registry[model].browse(cr, uid, res_id, context=context),
            'templates': templates,
            'model': model,
            'res_id': res_id,
            'field_body': field_body,
            'field_from': field_from,
            'field_subject': field_subject,
        }
        print '*', values
        return request.website.render("website_mail.designer_index", values)

    @http.route(['/website_mail/snippets'], type='json', auth="user", website=True)
    def snippets(self):
        return request.website._render('website_mail.email_designer_snippets')
