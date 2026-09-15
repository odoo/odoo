import copy

from odoo import api, models, tools
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    @tools.ormcache(
        "self.env.uid",
        "self.env.lang",
        'self.env.context.get("force_action")',
        "self._get_session_debug()",
    )
    def load_menus_root(self):
        root_menus = super().load_menus_root()
        if self.env.context.get("force_action"):
            root_menus = copy.deepcopy(root_menus)
            web_menus = self.load_web_menus(request.session.debug if request else False)
            for menu in root_menus["children"]:
                web_menu = web_menus.get(menu["id"])
                if (
                    not menu["action"]
                    and web_menu
                    and web_menu["actionModel"]
                    and web_menu["actionID"]
                ):
                    menu["action"] = f"{web_menu['actionModel']},{web_menu['actionID']}"

        _debug.perf.count(
            "root_menus_computed",
            user=self.env.uid,
            forced=bool(self.env.context.get("force_action")),
            menus=len(root_menus["children"]),
        )
        return root_menus
