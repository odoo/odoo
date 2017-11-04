# -*- coding: utf-8 -*-
import functools

from odoo import _
from odoo.exceptions import AccessError
from odoo.http import Controller, route, request, Response

def webservice(f):
    @functools.wraps(f)
    def wrap(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception as e:
            return Response(response=str(e), status=500)
    return wrap


class ImportModule(Controller):

    def check_user(self, uid=None):
        if uid is None:
            uid = request.uid
        is_admin = request.env['res.users'].browse(uid)._is_admin()
        if not is_admin:
            raise AccessError(_("Only administrators can upload a module"))

    @route('/base_import_module/login', type='http', auth='none', methods=['POST'], csrf=False)
    @webservice
    def login(self, login, password, db=None):
        if db and db != request.db:
            raise Exception(_("Could not select database '%s'") % db)
        uid = request.session.authenticate(request.db, login, password)
        if not uid:
            return Response(response="Wrong login/password", status=401)
        self.check_user(uid)
        return Response(headers={
            'X-CSRF-TOKEN': request.csrf_token(),
        })

    @route('/base_import_module/upload', type='http', auth='user', methods=['POST'])
    @webservice
    def upload(self, mod_file=None, force='', **kw):
        self.check_user()
        force = True if force == '1' else False
        return request.env['ir.module.module'].import_zipfile(mod_file, force=force)[0]
