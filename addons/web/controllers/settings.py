from typing import Any

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request

from ..tools import debug_log as dbg


class BaseSetup(http.Controller):
    @http.route("/base_setup/data", type="jsonrpc", auth="user", readonly=True)
    def base_setup_data(self, **kw) -> dict[str, Any]:
        dbg.lifecycle.debug("[base_setup] data: %s ignored=%s", dbg.req(), dbg.keys(kw))
        if not request.env.user.has_group("base.group_erp_manager"):
            dbg.logic.debug("[base_setup] data: not erp manager, refused")
            raise AccessError(_("Access Denied"))

        Users = request.env["res.users"]
        internal = [("share", "=", False)]
        with dbg.timer(request.env, "[base_setup] data: count + pending"):
            active_count = Users.search_count(internal)
            pending = Users.search(
                [*internal, ("log_ids", "=", False)], order="id desc"
            )
        pending_users = [(user.id, user.login) for user in pending[:10]]
        dbg.performance.debug(
            "[base_setup] data: active=%d pending=%d sample=%d",
            active_count,
            len(pending),
            len(pending_users),
        )
        return {
            "active_users": active_count,
            "pending_count": len(pending),
            "pending_users": pending_users,
            "action_pending_users": pending[:10]._action_show(),
        }

    @http.route("/base_setup/demo_active", type="jsonrpc", auth="user", readonly=True)
    def base_setup_is_demo(self, **kwargs) -> bool:
        demo = bool(
            request.env["ir.module.module"].search_count([("demo", "=", True)], limit=1)
        )
        dbg.logic.debug("[base_setup] demo_active: %s -> %s", dbg.req(), demo)
        return demo
