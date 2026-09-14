from typing import Any

from odoo import models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def load_web_menus(self, debug: bool) -> dict[str | int, dict[str, Any]]:
        menus = self.load_menus(debug)

        web_menus = {}
        for menu in menus.values():
            if not menu["id"]:
                web_menus["root"] = {
                    "id": "root",
                    "name": menu["name"],
                    "children": menu["children"],
                    "appID": False,
                    "xmlid": "",
                    "actionID": False,
                    "actionModel": False,
                    "actionPath": False,
                    "actionResModel": False,
                    "webIcon": None,
                    "webKeywords": None,
                    "webCategory": None,
                    "webCategorySequence": None,
                    "webIconData": None,
                    "webIconDataMimetype": None,
                }
            else:
                action_id = menu.get("action_id")
                action_model = menu.get("action_model")
                action_path = menu.get("action_path")
                action_res_model = menu.get("action_res_model")
                web_icon = menu.get("web_icon")
                web_icon_data = menu.get("web_icon_data")

                if menu["id"] == menu["app_id"]:
                    child = menu
                    while child and not action_id:
                        action_id = child["action_id"]
                        action_model = child["action_model"]
                        action_path = child["action_path"]
                        action_res_model = child["action_res_model"]
                        child = (
                            menus[child["children"][0]] if child["children"] else False
                        )

                    web_icon_raw = menu.get("web_icon") or ""
                    web_icon_parts = web_icon_raw.split(",") if web_icon_raw else []
                    icon_class = color = background_color = None
                    if web_icon_parts:
                        if len(web_icon_parts) >= 2:
                            icon_class, color = web_icon_parts[:2]
                        if len(web_icon_parts) == 3:
                            background_color = web_icon_parts[2]

                    if menu.get("web_icon_data"):
                        web_icon_data = f"data:{menu['web_icon_data_mimetype']};base64,{menu['web_icon_data']}"
                    elif background_color is not None:
                        web_icon = ",".join(
                            [icon_class or "", color or "", background_color]
                        )
                    else:
                        web_icon_data = "/web/static/img/default_icon_app.png"

                web_menus[menu["id"]] = {
                    "id": menu["id"],
                    "name": menu["name"],
                    "children": menu["children"],
                    "appID": menu["app_id"],
                    "xmlid": menu["xmlid"],
                    "actionID": action_id,
                    "actionModel": action_model,
                    "actionPath": action_path,
                    "actionResModel": action_res_model,
                    "webIcon": web_icon,
                    "webKeywords": menu.get("web_keywords"),
                    "webCategory": menu.get("web_category"),
                    "webCategorySequence": menu.get("web_category_sequence") or 0,
                    "webIconData": web_icon_data,
                    "webIconDataMimetype": menu["web_icon_data_mimetype"],
                }

        return web_menus
