import logging

from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.http import Controller, Response, request, route

_logger = logging.getLogger(__name__)


class ImportModule(Controller):
    @route(
        "/base_import_module/login_upload",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        save_session=False,
        readonly=False,
    )
    def login_upload(self, login, password, force="", mod_file=None, **kw):  # noqa: E8528 - authenticates the login and password it is posted
        try:
            if not request.db:
                raise UserError("Could not select a database.")  # noqa: E8505 no database, so no language
            credential = {"login": login, "password": password, "type": "password"}
            request.session.authenticate(request.env, credential)
            # request.env.uid is None in case of MFA
            if request.env.uid and request.env.user._is_admin():
                return request.env["ir.module.module"]._import_zipfile(
                    mod_file, force=force == "1"
                )[0]
            raise AccessError(request.env._("Only administrators can upload a module"))
        except (AccessDenied, AccessError) as e:
            return Response(response=str(e), status=403)
        except UserError as e:
            return Response(response=str(e), status=400)
        except Exception as e:
            _logger.exception("Module upload failed")
            return Response(response=str(e), status=500)
