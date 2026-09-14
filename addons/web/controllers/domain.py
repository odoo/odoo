from odoo import _, http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import Controller, request
from odoo.tools import SQL
from odoo.tools.misc import mute_logger

from ..tools import debug_log as dbg
from .utils import is_user_internal


class Domain(Controller):
    @http.route("/web/domain/validate", type="jsonrpc", auth="user", readonly=True)
    def is_domain_valid(self, model: str, domain: list) -> bool:
        dbg.lifecycle.debug(
            "[domain:%s] validate: %s terms=%s", model, dbg.req(), dbg.count(domain)
        )
        if not is_user_internal(request.session.uid):
            dbg.logic.debug("[domain:%s] validate: not internal, refused", model)
            raise AccessError(_("This endpoint is reserved to internal users."))
        Model = request.env.get(model)
        if Model is None:
            dbg.logic.debug("[domain:%s] validate: unknown model", model)
            raise ValidationError(_("Invalid model: %s", model))
        try:
            with (
                dbg.timer(request.env, "[domain:%s] validate: search + EXPLAIN", model),
                request.env.cr.savepoint(flush=False),
            ):
                query = Model.sudo()._search(domain)

                sql = SQL("EXPLAIN %s", query.select())
                with mute_logger("odoo.db"):
                    request.env.cr.execute(sql)
            dbg.logic.debug("[domain:%s] validate: valid", model)
            return True
        except Exception as exc:
            dbg.logic.debug(
                "[domain:%s] validate: invalid (%s)", model, type(exc).__name__
            )
            return False
