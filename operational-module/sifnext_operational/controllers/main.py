from odoo import http
from odoo.http import request


class SifnextRoleController(http.Controller):

    @http.route(
        "/sifnext_operational/switch_role",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def switch_role(self, role):
        user = request.env.user

        # Validasi role
        if role not in ("user", "ga"):
            return {
                "success": False,
                "message": "Role tidak valid.",
            }

        # Operational User
        if role == "user":
            if not user.has_group(
                "sifnext_operational.group_sifnext_operational_user"
            ):
                return {
                    "success": False,
                    "message": "User tidak memiliki role Operational User.",
                }

        # General Affair
        if role == "ga":
            if not user.has_group(
                "sifnext_operational.group_sifnext_operational_ga"
            ):
                return {
                    "success": False,
                    "message": "User tidak memiliki role General Affair.",
                }

        # Simpan role aktif
        user.sudo().write({
            "sifnext_active_role": role,
        })

        return {
            "success": True,
            "role": role,
        }