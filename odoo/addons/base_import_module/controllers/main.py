# -*- coding: utf-8 -*-
import functools

from odoo import _
from odoo.exceptions import AccessError
from odoo.http import Controller, route, request, Response


class ImportModule(Controller):
    @route(
        '/base_import_module/login_upload',
        type='http', auth='none', methods=['POST'], csrf=False, save_session=False)
    def login_upload(self, login, password, force='', mod_file=None, **kw):
        try:
            if not request.db:
                raise Exception(_("Could not select database '%s'", request.db))
            request.session.authenticate(request.db, login, password)
            # request.uid is None in case of MFA
            if request.uid and request.env.user._is_admin():
                return request.env['ir.module.module']._import_zipfile(mod_file, force=force == '1')[0]
            raise AccessError(_("Only administrators can upload a module"))
        except Exception as e:
            return Response(response=str(e), status=500)
