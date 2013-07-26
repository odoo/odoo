# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.controllers import main
from openerp.addons.web.http import request


class website(http.Controller):
    public_user_id = None

    def get_uid(self):
        try:
            request.session.check_security()
            uid = request.session._uid
        except http.SessionExpiredException:
            if not website.public_user_id:
                data_obj = request.registry['ir.model.data']
                website.public_user_id = data_obj.get_object_reference(request.cr, openerp.SUPERUSER_ID, 'website', 'public_user')[1]
            uid = website.public_user_id

        return uid

    def isloggued(self):
        return website.public_user_id != self.get_uid()

    def render(self, cr, uid, template, add_values={}):
        script = "\n".join(['<script type="text/javascript" src="%s"></script>' % i for i in main.manifest_list('js', db=request.db)])
        css = "\n".join('<link rel="stylesheet" href="%s">' % i for i in main.manifest_list('css', db=request.db))
        _values = {
            'request': request,
            'registry': request.registry,
            'cr': cr,
            'uid': uid,
            'script': script,
            'css': css,
            'host_url': request.httprequest.host_url,
        }
        _values.update(add_values)
        return request.registry.get("ir.ui.view").render(cr, uid, template, _values)

    @staticmethod
    def route(*args, **kwargs):
        def wrap(_funct):
            @http.route(*args, **kwargs)
            def wrapper(self, *a, **k):
                return _funct(self, request.cr, self.get_uid(), *a, **k)
            return wrapper
        return wrap
