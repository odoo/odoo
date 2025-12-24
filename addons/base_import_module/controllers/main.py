# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.http import Controller, route, request, Response


class ImportModule(Controller):
    @route(
        '/base_import_module/login_upload',
        type='http', auth='none', methods=['POST'], csrf=False, save_session=False)
    def login_upload(self, login, password, force='', mod_file=None, **kw):
        try:
            self._check_for_database()
            credential = {'login': login, 'password': password, 'type': 'password'}
            request.session.authenticate(request.env, credential)
            self._check_admin_rights()
            return request.env['ir.module.module']._import_zipfile(mod_file, force=force == '1')[0]
        except Exception as e:
            return Response(response=str(e), status=500)

    def _check_for_database(self):
        if not request.db:
            raise Exception(self.env._("Could not select database '%s'", request.db))

    def _check_admin_rights(self):
        # request.env.uid is None in case of MFA
        if not request.env.uid and not request.env.user._is_admin():
            raise AccessError(self.env._("Only administrators can upload a module"))
