# -*- coding: utf-8 -*-
import functools
import logging
import traceback

from odoo import _
from odoo.exceptions import AccessError, UserError
from odoo.http import Controller, route, request, Response

_logger = logging.getLogger(__name__)


class ImportModule(Controller):
    @route(
        '/base_import_module/login_upload',
        type='http', auth='none', methods=['POST'], csrf=False, save_session=False)
    def login_upload(self, login, password, force='', mod_file=None, **kw):

        try:
            if not request.db:
                raise Exception(_("Could not select database '%s'", request.db))

            credential = {'login': login, 'password': password, 'type': 'password'}
            request.session.authenticate(request.env, credential)

            if request.env.uid and request.env.user._is_admin():
                return request.env['ir.module.module']._import_zipfile(
                    mod_file, force=force == '1'
                )[0]

            raise AccessError(_("Only administrators can upload a module"))

        except UserError as e:
            # return clean error to client
            return Response(response=str(e), status=400)

        except Exception as e:
            # log full traceback
            _logger.error("Deploy failed:\n%s", traceback.format_exc())
            return Response(response="Server error: %s" % str(e), status=500)
