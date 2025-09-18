from typing import Any

from odoo import models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def load_web_menus(self, debug: bool) -> dict[str | int, dict[str, Any]]:
        """Loads all menu items (all applications and their sub-menus) and
        processes them to be used by the webclient. Mainly, it associates with
        each application (top level menu) the action of its first child menu
        that is associated with an action (recursively), i.e. with the action
        to execute when the opening the app.

        :return: the menus (including the images in Base64)
        """
        menus = self.load_menus(debug)

        web_menus = {}
        for menu in menus.values():
            if not menu["id"]:
                # special root menu case
                web_menus["root"] = {
                    "id": "root",
                    "name": menu["name"],
                    "children": menu["children"],
                    "appID": False,
                    "xmlid": "",
                    "actionID": False,
                    "actionModel": False,
                    "actionPath": False,
                    "webIcon": None,
                    "webIconData": None,
                    "webIconDataMimetype": None,
                    "backgroundImage": menu.get("backgroundImage"),
                }
            else:
                action_id = menu["action_id"]
                action_model = menu["action_model"]
                action_path = menu["action_path"]
                web_icon = menu["web_icon"]
                web_icon_data = menu["web_icon_data"]

                if menu["id"] == menu["app_id"]:
                    # if it's an app take action of first (sub)child having one defined
                    child = menu
                    while child and not action_id:
                        action_id = child["action_id"]
                        action_model = child["action_model"]
                        action_path = child["action_path"]
                        child = (
                            menus[child["children"][0]] if child["children"] else False
                        )

                    web_icon_raw = menu.get("web_icon", "")
                    web_icon_parts = web_icon_raw and web_icon_raw.split(",")
                    icon_class = color = background_color = None
                    if web_icon_parts:
                        if len(web_icon_parts) >= 2:
                            icon_class, color = web_icon_parts[:2]
                        if len(web_icon_parts) == 3:
                            background_color = web_icon_parts[2]

                    if menu.get("web_icon_data"):
                        web_icon_data = f"data:{menu['web_icon_data_mimetype']};base64,{menu['web_icon_data']}"
                    elif background_color is not None:  # Could split in three parts?
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
                    "webIcon": web_icon,
                    "webIconData": web_icon_data,
                    "webIconDataMimetype": menu["web_icon_data_mimetype"],
                }

        return web_menus
