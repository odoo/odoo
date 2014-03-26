# -*- coding: utf-8 -*-
import functools
import os
import zipfile
from os.path import join as opj

import openerp
from openerp.http import Controller, route, request, Response

MAX_FILE_SIZE = 100 * 1024 * 1024 # in megabytes

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
        is_admin = request.registry['res.users'].has_group(request.cr, uid, 'base.group_erp_manager')
        if not is_admin:
            raise openerp.exceptions.AccessError("Only administrators can upload a module")

    @route('/base_import_module/login', type='http', auth='none', methods=['POST'])
    @webservice
    def login(self, login, password, db=None):
        if db and db != request.db:
            raise Exception("Could not select database '%s'" % db)
        uid = request.session.authenticate(request.db, login, password)
        if not uid:
            return Response(response="Wrong login/password", status=401)
        self.check_user(uid)
        return "ok"

    @route('/base_import_module/upload', type='http', auth='user', methods=['POST'])
    @webservice
    def upload(self, mod_file=None, **kw):
        self.check_user()
        imm = request.registry['ir.module.module']

        if not mod_file:
            raise Exception("No file sent.")
        if not zipfile.is_zipfile(mod_file):
            raise Exception("Not a zipfile.")

        success = []
        errors = dict()
        with zipfile.ZipFile(mod_file, "r") as z:
            for zf in z.filelist:
                if zf.file_size > MAX_FILE_SIZE:
                    raise Exception("File '%s' exceed maximum allowed file size" % zf.filename)

            with openerp.tools.osutil.tempdir() as module_dir:
                z.extractall(module_dir)
                dirs = [d for d in os.listdir(module_dir) if os.path.isdir(opj(module_dir, d))]
                for mod_name in dirs:
                    try:
                        # assert mod_name.startswith('theme_')
                        path = opj(module_dir, mod_name)
                        imm.import_module(request.cr, request.uid, mod_name, path, context=request.context)
                        success.append(mod_name)
                    except Exception, e:
                        errors[mod_name] = str(e)
        r = ["Successfully imported module '%s'" % mod for mod in success]
        for mod, error in errors.items():
            r.append("Error while importing module '%s': %r" % (mod, error))
        return '\n'.join(r)
