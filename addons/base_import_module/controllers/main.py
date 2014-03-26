# -*- coding: utf-8 -*-
import os
import zipfile
from os.path import join as opj

import openerp
from openerp.http import Controller, route, request

MAX_FILE_SIZE = 100 * 1024 * 1024 # in megabytes

class ImportModule(Controller):

    @route('/base_import_module/check', type='http', auth='user', methods=['GET'])
    def check(self):
        assert request.db # TODO: custom ensure_db?
        assert request.uid == openerp.SUPERUSER_ID # TODO: check admin group
        return 'ok'

    @route('/base_import_module/upload', type='http', auth='user', methods=['POST'])
    def upload(self, mod_file=None, **kw):
        assert request.db # TODO: custom ensure_db?
        assert request.uid == openerp.SUPERUSER_ID # TODO: check admin group

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
                    raise Exception("File %r exceed maximum allowed file size" % zf.filename)

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
        r = ["Successfully imported module %r" % mod for mod in success]
        for mod, error in errors.items():
            r.append("Error while importing module %r: %r" % (mod, error))
        return '\n'.join(r)
