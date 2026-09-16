import time
from typing import Any

from odoo import _, fields, models
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.libs.json import loads as json_loads

_debug = DebugLog(__name__)


class ResUsersIdentitycheck(models.TransientModel):
    _name = "res.users.identitycheck"
    _description = "Password Check Wizard"

    request = fields.Char(
        readonly=True,
        groups=fields.NO_ACCESS,
    )
    auth_method = fields.Selection(
        selection=[("password", "Password")],
        default=lambda self: self._default_auth_method(),
    )
    password = fields.Char(store=False)

    def _default_auth_method(self) -> str:
        return "password"

    def _check_identity(self) -> None:
        try:
            credential = {
                "login": self.env.user.login,
                "password": self.env.context.get("password"),
                "type": "password",
            }
            user = self.env.user
            with user._assert_can_auth(user=user.id):
                user._check_credentials(credential, {"interactive": True})
        except AccessDenied:
            _debug.logic("identity_check_failed", uid=self.env.uid)
            raise UserError(
                _(
                    "Incorrect Password, try again or click on Forgot Password to reset your password."
                )
            ) from None

    def run_check(self) -> Any:
        if not request:
            _debug.logic("identity_check_refused", reason="no_request")
            raise UserError(_("This method can only be accessed over HTTP."))
        self._check_identity()

        if not self.sudo().request:
            _debug.logic("identity_check_refused", reason="no_pending_method")
            raise UserError(_("There is no method to run after the identity check."))
        ctx, model, ids, method_name, args, kwargs = json_loads(self.sudo().request)
        _debug.logic(
            "identity_check_passed", uid=self.env.uid, model=model, method=method_name
        )
        method = getattr(self.env(context=ctx)[model].browse(ids), method_name)
        if not getattr(method, "__has_check_identity", False):
            _debug.logic(
                "identity_check_refused", reason="unmarked_method", method=method_name
            )
            raise UserError(
                _("This method is not allowed for identity-checked execution.")
            )
        request.session["identity-check-last"] = time.time()
        return method(*args, **kwargs)
