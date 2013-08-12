# -*- coding: utf-8 -*-
import simplejson

import openerp
from openerp.osv import osv
from openerp.addons.web import http
from openerp.addons.web.controllers import main
from openerp.addons.web.http import request


def auth_method_public():
    registry = openerp.modules.registry.RegistryManager.get(request.db)
    if not request.session.uid:
        request.uid = registry['website'].get_public_user().id
    else:
        request.uid = request.session.uid
http.auth_methods['public'] = auth_method_public


class website(osv.osv):
    _name = "website" # Avoid website.website convention for conciseness (for new api). Got a special authorization from xmo and rco
    _description = "Website"

    public_user = None

    def get_public_user(self):
        if not self.public_user:
            ref = request.registry['ir.model.data'].get_object_reference(request.cr, openerp.SUPERUSER_ID, 'website', 'public_user')
            self.public_user = request.registry[ref[0]].browse(request.cr, openerp.SUPERUSER_ID, ref[1])
        return self.public_user

    def get_rendering_context(self, additional_values=None):
        debug = 'debug' in request.params
        is_public_user = request.uid == self.get_public_user().id
        values = {
            'debug': debug,
            'is_public_user': is_public_user,
            'editable': not is_public_user,
            'request': request,
            'registry': request.registry,
            'cr': request.cr,
            'uid': request.uid,
            'host_url': request.httprequest.host_url,
            'res_company': request.registry['res.company'].browse(request.cr, openerp.SUPERUSER_ID, 1),
            'json': simplejson,
        }
        if values['editable']:
            values.update({
                'script': "\n".join(['<script type="text/javascript" src="%s"></script>' % i for i in main.manifest_list('js', db=request.db, debug=debug)]),
                'css': "\n".join('<link rel="stylesheet" href="%s">' % i for i in main.manifest_list('css', db=request.db, debug=debug))
            })
        if additional_values:
            values.update(additional_values)
        return values

    def render(self, template, values={}):
        context = {
            'inherit_branding': values.get('editable', False),
        }
        return request.registry.get("ir.ui.view").render(request.cr, request.uid, template, values, context=context)
