from datetime import datetime

from odoo import api, models


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    def unlink(self):
        event_updates = {}
        website_event_menus = self.env["website.event.menu"].search(
            [("menu_id", "in", self.ids)]
        )
        for event_menu in website_event_menus:
            to_update = event_updates.setdefault(event_menu.event_id, [])
            for (
                menu_type,
                fname,
            ) in event_menu.event_id._get_menu_type_field_matching().items():
                if event_menu.menu_type == menu_type:
                    to_update.append(fname)

        unlinked_menus = self

        if website_event_menus:
            cascaded_menus = website_event_menus.view_id.page_ids.menu_ids
            unlinked_menus = self - cascaded_menus
            website_event_menus.unlink()

        res = super(WebsiteMenu, unlinked_menus).unlink()

        for event, to_update in event_updates.items():
            if to_update:
                event.write(dict.fromkeys(to_update, False))

        return res

    @api.model
    def save(self, website_id, data):

        old_menu_ids = [
            menu["id"] for menu in data["data"] if isinstance(menu["id"], int)
        ]
        has_new_menus = any(isinstance(menu["id"], str) for menu in data["data"])
        res = super().save(website_id, data)

        if not has_new_menus:
            return res

        menus_by_parent_id = {}
        for menu in data["data"]:
            if not menu.get("parent_id"):
                continue
            if not menus_by_parent_id.get(menu["parent_id"]):
                menus_by_parent_id[menu["parent_id"]] = []

            menus_by_parent_id[menu["parent_id"]].append(menu)

        for parent_id, menus in menus_by_parent_id.items():
            new_menus = [menu for menu in menus if menu["id"] not in old_menu_ids]
            if not new_menus:
                continue

            parent = self.env["website.menu"].browse(parent_id)
            while parent.parent_id:
                parent = parent.parent_id

            if parent_event_menu := self.env["website.event.menu"].search(  # noqa: E8507 - one probe per created menu, on that menu's own root
                [("menu_id.parent_id", "=", parent.id)], limit=1
            ):
                event_url = parent_event_menu.event_id.website_url.rstrip("/")
                event_menu_values = []
                for new_menu in new_menus:
                    menu_record = self.env["website.menu"].browse(new_menu["id"])
                    menu_record_url = menu_record.url.lstrip("/")
                    if not menu_record_url or menu_record_url == "#":
                        menu_record_url = f"t{int(datetime.now().timestamp())}"

                    menu_record.write({"url": f"{event_url}/page/{menu_record_url}"})
                    event_menu_values.append(
                        {
                            "menu_id": menu_record.id,
                            "event_id": parent_event_menu.event_id.id,
                            "menu_type": "other",
                        }
                    )

                self.env["website.event.menu"].sudo().create(event_menu_values)

        return res
