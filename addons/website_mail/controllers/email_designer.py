# -*- coding: utf-8 -*-

from urllib import urlencode

from openerp.addons.web import http
from openerp.addons.web.http import request


class WebsiteEmailDesigner(http.Controller):

    @http.route('/website_mail/email_designer', type='http', auth="user", website=True)
    def index(self, model, res_id, template_model=None, **kw):
        if not model or not model in request.registry or not res_id:
            return request.redirect('/')
        model_cols = request.registry[model]._all_columns
        if 'body' not in model_cols and 'body_html' not in model_cols or \
           'email' not in model_cols and 'email_from' not in model_cols or \
           'name' not in model_cols and 'subject' not in model_cols:
            return request.redirect('/')
        res_id = int(res_id)
        obj_ids = request.registry[model].exists(request.cr, request.uid, [res_id], context=request.context)
        if not obj_ids:
            return request.redirect('/')
        # try to find fields to display / edit -> as t-field is static, we have to limit
        # the available fields to a given subset
        email_from_field = 'email'
        if 'email_from' in model_cols:
            email_from_field = 'email_from'
        subject_field = 'name'
        if 'subject' in model_cols:
            subject_field = 'subject'
        body_field = 'body'
        if 'body_html' in model_cols:
            body_field = 'body_html'

        cr, uid, context = request.cr, request.uid, request.context
        record = request.registry[model].browse(cr, uid, res_id, context=context)

        values = {
            'record': record,
            'templates': None,
            'model': model,
            'res_id': res_id,
            'email_from_field': email_from_field,
            'subject_field': subject_field,
            'body_field': body_field,
        }

        if getattr(record, body_field):
            values['mode'] = 'email_designer'
        else:
            if kw.get('enable_editor'):
                kw.pop('enable_editor')
                fragments = dict(model=model, res_id=res_id, **kw)
                if template_model:
                    fragments['template_model'] = template_model
                return request.redirect('/website_mail/email_designer?%s' % urlencode(fragments))
            values['mode'] = 'email_template'

        tmpl_obj = request.registry['email.template']
        if template_model:
            tids = tmpl_obj.search(cr, uid, [('model', '=', template_model)], context=context)
        else:
            tids = tmpl_obj.search(cr, uid, [], context=context)
        templates = tmpl_obj.browse(cr, uid, tids, context=context)
        values['templates'] = templates

        return request.website.render("website_mail.email_designer", values)

    @http.route(['/website_mail/snippets'], type='json', auth="user", website=True)
    def snippets(self):
        return request.website._render('website_mail.email_designer_snippets')
