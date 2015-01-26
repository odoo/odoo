# -*- coding: utf-8 -*-

from urllib import urlencode

from openerp import addons
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.mail import html_sanitize


class WebsiteEmailDesigner(http.Controller):

    @http.route(['/website_mail/snippets'], type='json', auth="user", website=True)
    def snippets(self):
        return request.website._render('website_mail.email_designer_snippets')


class Website(addons.website.controllers.main.Website):

    #------------------------------------------------------
    # Backend email template field
    #------------------------------------------------------
    @http.route('/website_mail/field/email', type='http', auth="public", website=True)
    def FieldTextHtmlEmail(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        kwargs['template'] = "website_mail.FieldTextHtmlEmail"
        return self.FieldTextHtml(model, res_id, field, callback, **kwargs)

    @http.route('/website_mail/field/email_template', type='http', auth="public", website=True)
    def FieldTextHtmlEmailTemplate(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        tmpl_obj = request.registry['mail.template']
        tids = tmpl_obj.search(cr, uid, kwargs.get('template_model') and [('model', '=', kwargs.get('template_model'))] or [], context=context)
        kwargs['templates'] = tmpl_obj.browse(cr, uid, tids, context=context)
        kwargs['snippets'] = 'snippets' not in kwargs and '/website_mail/snippets' or kwargs['snippets']
        return self.FieldTextHtmlEmail(model, res_id, field, callback, **kwargs)
