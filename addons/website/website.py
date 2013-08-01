# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.controllers import main
from openerp.addons.web.http import request


def auth_method_public():
    registry = openerp.modules.registry.RegistryManager.get(request.db)
    with registry.cursor() as cr:
        request.public_uid = request.registry['ir.model.data'].get_object_reference(cr, openerp.SUPERUSER_ID, 'website', 'public_user')[1]
        if not request.session.uid:
            request.uid = request.public_uid
        else:
            request.uid = request.session.uid
http.auth_methods['public'] = auth_method_public


class website(object):
    def render(self, template, add_values={}):
        script = "\n".join(['<script type="text/javascript" src="%s"></script>' % i for i in main.manifest_list('js', db=request.db)])
        css = "\n".join('<link rel="stylesheet" href="%s">' % i for i in main.manifest_list('css', db=request.db))
        _values = {
            'editable': request.uid != request.public_uid,
            'request': request,
            'registry': request.registry,
            'cr': request.cr,
            'uid': request.uid,
            'script': script,
            'css': css,
            'host_url': request.httprequest.host_url,
        }
        _values.update(add_values)
        return request.registry.get("ir.ui.view").render(request.cr, request.uid, template, _values)
website = website()