from odoo.exceptions import AccessError
from odoo.http import Controller, request, route
from odoo.tools.translate import _

from ..tools import debug_log as dbg


class View(Controller):
    @route("/web/view/edit_custom", type="jsonrpc", auth="user")
    def edit_custom(self, custom_id: int, arch: str) -> dict[str, bool]:
        dbg.lifecycle.debug(
            "[custom_view:%s] edit: %s arch_len=%d", custom_id, dbg.req(), len(arch)
        )
        custom_view = request.env["ir.ui.view.custom"].sudo().browse(custom_id)
        if custom_view.user_id != request.env.user:
            dbg.logic.debug(
                "[custom_view:%s] edit: owner uid=%s != uid=%s, refused",
                custom_id,
                custom_view.user_id.id,
                request.env.uid,
            )
            raise AccessError(
                _(
                    "Custom view %(view)s does not belong to user %(user)s",
                    view=custom_id,
                    user=request.env.user.login,
                )
            )
        with dbg.timer(request.env, "[custom_view:%s] write arch", custom_id):
            custom_view.write({"arch": arch})
        return {"result": True}
