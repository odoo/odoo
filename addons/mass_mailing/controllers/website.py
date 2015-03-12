# -*- coding: utf-8 -*-

from openerp import http
from openerp.addons.website.controllers.main import Website


class Website(Website):

    @http.route(["/website_mass_mailing/field/popup_content"], type='http', auth="public", website=True)
    def FieldTextHtmlPopupTemplate(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        kwargs['snippets'] = 'snippets' not in kwargs and '/website/snippets' or kwargs['snippets']
        kwargs['dont_load_assets'] = False
        kwargs['template'] = "mass_mailing.FieldTextHtmlPopupContent"
        return self.FieldTextHtml(model, res_id, field, callback, **kwargs)
