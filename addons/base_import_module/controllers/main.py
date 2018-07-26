# -*- coding: utf-8 -*-
import functools
import openerp
from openerp.http import Controller, route, request, Response

def webservice(f):
    @functools.wraps(f)
    def wrap(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception, e:
            return Response(response=str(e), status=500)
    return wrap

class ImportModule(Controller):

    def check_user(self, uid=None):
        if uid is None:
            uid = request.uid
        is_admin = request.registry['res.users']._is_admin(request.cr, uid, [uid])
        if not is_admin:
            raise openerp.exceptions.AccessError("Only administrators can upload a module")

    @route('/base_import_module/login', type='http', auth='none', methods=['POST'], csrf=False)
    @webservice
    def login(self, login, password, db=None):
        if db and db != request.db:
            raise Exception("Could not select database '%s'" % db)
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
        return request.registry['ir.module.module'].import_zipfile(request.cr, request.uid, mod_file, force=force, context=request.context)[0]
