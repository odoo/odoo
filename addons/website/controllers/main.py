# -*- coding: utf-8 -*-
import openerp
from openerp.addons.web import http
from openerp.addons.web.controllers.main import manifest_list
from urllib import quote_plus
from openerp.addons.web.http import request

def template_values():
    script = "\n".join(['<script type="text/javascript" src="%s"></script>' % i for i in manifest_list('js', db=request.db)])
    values = {
        'request': request,
        'registry': request.registry,
        'cr': request.cr,
        'uid': request.session._uid,
        'script' : script,
    }
    return values

class Website(openerp.addons.web.controllers.main.Home):

    @http.route('/', type='http', auth="db")
    def index(self, **kw):
        return self.page("website.homepage")

    @http.route('/admin', type='http', auth="none")
    def admin(self, *args, **kw):
        return super(Website, self).index(*args, **kw)

    @http.route('/page/<path:path>', type='http', auth="db")
    def page(self, path):
        #def get_html_head():
        #    head += ['<link rel="stylesheet" href="%s">' % i for i in manifest_list('css', db=request.db)]
        #modules = request.registry.get("ir.module.module").search_read(request.cr, openerp.SUPERUSER_ID, fields=['id', 'shortdesc', 'summary', 'icon_image'], limit=50)
        try:
            request.session.check_security()
            editable = True
            uid = request.session._uid
        except http.SessionExpiredException:
            editable = False
            uid = openerp.SUPERUSER_ID
        context = {
            'inherit_branding': editable
        }
        values = template_values()
        company = request.registry['res.company'].browse(request.cr, uid, 1, context=context)
        values.update({
            'uid': uid,
            'editable': editable,
            'res_company': company,
        })
        values['google_map_url'] = "http://maps.googleapis.com/maps/api/staticmap?center=%s&sensor=false&zoom=8&size=298x298" \
                % quote_plus('%s, %s %s, %s' % (company.street, company.city, company.zip, company.country_id and company.country_id.name_get()[0][1] or ''))
        html = request.registry.get("ir.ui.view").render(request.cr, uid, path, values, context)
        return html

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
