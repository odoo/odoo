from typing import Any

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request


class BaseSetup(http.Controller):
    """HTTP endpoints for the General Settings dashboard widgets."""

    @http.route("/base_setup/data", type="jsonrpc", auth="user")
    def base_setup_data(self, **kw) -> dict[str, Any]:
        """Return active/pending user counts and a pending-user action for the invite widget."""
        if not request.env.user.has_group("base.group_erp_manager"):
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
        """Return whether the database was initialised with demo data."""
        return bool(request.env["ir.module.module"].search_count([("demo", "=", True)]))
