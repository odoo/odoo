# -*- coding: utf-8 -*-
import urllib

import openerp
from openerp.addons.web import http
from openerp.addons.web.controllers.main import manifest_list
from openerp.addons.web.http import request

def template_values():
    script = "\n".join(['<script type="text/javascript" src="%s"></script>' % i for i in manifest_list('js', db=request.db)])
    css = "\n".join('<link rel="stylesheet" href="%s">' % i for i in manifest_list('css', db=request.db))
    try:
        request.session.check_security()
        loggued = True
        uid = request.session._uid
    except http.SessionExpiredException:
        loggued = False
        uid = openerp.SUPERUSER_ID
    values = {
        'loggued': loggued,
        'editable': loggued,
        'request': request,
        'registry': request.registry,
        'cr': request.cr,
        'uid': uid,
        'script': script,
        'css': css,
        'host_url': request.httprequest.host_url,
    }
    return values

class Website(openerp.addons.web.controllers.main.Home):
    @http.route('/', type='http', auth="admin")
    def index(self, **kw):
        return self.page("website.homepage")

    @http.route('/admin', type='http', auth="none")
    def admin(self, *args, **kw):
        return super(Website, self).index(*args, **kw)

    @http.route('/pagenew/<path:path>', type='http', auth="admin")
    def pagenew(self, path):
        values = template_values()
        uid = values['uid']
        imd = request.registry['ir.model.data']
        view_model, view_id = imd.get_object_reference(request.cr, uid, 'website', 'default_page')
        newview_id = request.registry['ir.ui.view'].copy(request.cr, uid, view_id)
        if '.' in path:
            module, idname = path.split('.')
        else:
            module = False
            idname = path
        imd.create(request.cr, uid, {
            'name': idname,
            'module': module,
            'model': 'ir.ui.view',
            'res_id': newview_id,
        })
        # TODO: replace by a redirect
        return self.page(path)

    @http.route('/page/<path:path>', type='http', auth="admin")
    def page(self, path):
        #def get_html_head():
        #    head += ['<link rel="stylesheet" href="%s">' % i for i in manifest_list('css', db=request.db)]
        #modules = request.registry.get("ir.module.module").search_read(request.cr, openerp.SUPERUSER_ID, fields=['id', 'shortdesc', 'summary', 'icon_image'], limit=50)
        values = template_values()
        uid = values['uid']
        context = {
            'inherit_branding': values['editable'],
        }
        company = request.registry['res.company'].browse(request.cr, uid, 1, context=context)
        values.update(
            res_company=company,
            path=path,
            google_map_url="http://maps.googleapis.com/maps/api/staticmap?" + urllib.urlencode({
                'center': '%s, %s %s, %s' % (company.street, company.city, company.zip, company.country_id and company.country_id.name_get()[0][1] or ''),
                'sensor': 'false',
                'zoom': '8',
                'size': '298x298',
            }),
        )
        try:
            html = request.registry.get("ir.ui.view").render(request.cr, uid, path, values, context)
        except ValueError, e:
            html = request.registry.get("ir.ui.view").render(request.cr, uid, 'website.404', values, context)
        return html

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
