# -*- coding: utf-8 -*-
import openerp
from openerp.addons.web import http
from openerp.addons.web.controllers.main import manifest_list
from openerp.addons.web.http import request

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
        script = "\n".join(['<script type="text/javascript" src="%s"></script>' % i for i in manifest_list('js', db=request.db)])
        values = {
            'script' : script,
            'editable': editable,
            'request': request,
            'registry': request.registry,
            'cr': request.cr,
            'uid': uid,
            'res_company': request.registry['res.company'].browse(request.cr, uid, 1, context=context),
        }
        html = request.registry.get("ir.ui.view").render(request.cr, uid, path, values, context)
        return html

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
