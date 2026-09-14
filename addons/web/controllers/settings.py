from typing import Any

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request

from ..tools import debug_log as dbg


class BaseSetup(http.Controller):
    @http.route("/base_setup/data", type="jsonrpc", auth="user")
    def base_setup_data(self, **kw) -> dict[str, Any]:
        dbg.lifecycle.debug("[base_setup] data: %s ignored=%s", dbg.req(), dbg.keys(kw))
        if not request.env.user.has_group("base.group_erp_manager"):
            dbg.logic.debug("[base_setup] data: not erp manager, refused")
            raise AccessError(_("Access Denied"))

        cr = request.env.cr
        cr.execute("""
            SELECT count(*)
              FROM res_users
             WHERE active = true AND share = false
        """)
        active_count = cr.fetchone()[0]

        cr.execute("""
            SELECT count(u.*)
              FROM res_users u
             WHERE active = true
               AND share = false
               AND NOT exists(SELECT 1 FROM res_users_log WHERE create_uid = u.id)
        """)
        pending_count = cr.fetchone()[0]

        cr.execute("""
            SELECT id, login
              FROM res_users u
             WHERE active = true
               AND share = false
               AND NOT exists(SELECT 1 FROM res_users_log WHERE create_uid = u.id)
          ORDER BY id DESC
             LIMIT 10
        """)
        pending_users = cr.fetchall()
        dbg.performance.debug(
            "[base_setup] data: active=%d pending=%d sample=%d (three counts, one scan)",
            active_count,
            pending_count,
            len(pending_users),
        )
        action_pending_users = (
            request.env["res.users"]
            .browse([uid for (uid, login) in pending_users])
            ._action_show()
        )

        return {
            "active_users": active_count,
            "pending_count": pending_count,
            "pending_users": pending_users,
            "action_pending_users": action_pending_users,
        }

    @http.route("/base_setup/demo_active", type="jsonrpc", auth="user")
    def base_setup_is_demo(self, **kwargs) -> bool:
        demo = bool(
            request.env["ir.module.module"].search_count([("demo", "=", True)], limit=1)
        )
        dbg.logic.debug("[base_setup] demo_active: %s -> %s", dbg.req(), demo)
        return demo
