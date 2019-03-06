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

    @route(
        '/base_import_module/login_upload',
        type='http', auth='none', methods=['POST'], csrf=False, save_session=False)
    @webservice
    def login_upload(self, login, password, db=None, force='', mod_file=None, **kw):
        if db and db != request.db:
            raise Exception(_("Could not select database '%s'") % db)
        uid = request.session.authenticate(request.db, login, password)
        self.check_user(uid)
        force = True if force == '1' else False
        return request.env['ir.module.module'].import_zipfile(mod_file, force=force)[0]
