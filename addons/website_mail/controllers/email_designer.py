# -*- coding: utf-8 -*-

# from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request


class WebsiteEmailDesigner(http.Controller):

    @http.route('/website_mail/email_designer/<model("email.template"):template>/', type='http', auth="user", website=True, multilang=True)
    def index(self, template, **kw):
        values = {
            'template': template,
        }
        print template
        return request.website.render("website_mail.designer_index", values)

    @http.route(['/website_mail/snippets'], type='json', auth="user", website=True)
    def snippets(self):
        return request.website._render('website_mail.email_designer_snippets')
