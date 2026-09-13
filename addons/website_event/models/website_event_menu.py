from datetime import datetime

from odoo import api, fields, models


class WebsiteEventMenu(models.Model):
    _name = "website.event.menu"
    _inherit = "mixin.website.seo.metadata"
    _description = "Website Event Menu"
    _rec_name = "menu_id"

    menu_id = fields.Many2one(
        comodel_name="website.menu",
        ondelete="cascade",
    )
    event_id = fields.Many2one(
        comodel_name="event.event",
        index="btree_not_null",
        ondelete="cascade",
    )
    view_id = fields.Many2one(
        comodel_name="ir.ui.view",
        ondelete="cascade",
        help="Used when not being an url based menu",
    )
    menu_type = fields.Selection(
        selection=[
            ("community", "Community Menu"),
            ("introduction", "Home"),
            ("register", "Practical"),
            ("other", "Other"),
        ],
        required=True,
    )

    def copy(self, default=None):
        new_menus = super().copy(default=default)
        for new_menu, old_menu in zip(new_menus, self, strict=True):
            if not old_menu.view_id:
                continue
            view = (
                self.env["ir.ui.view"]  # noqa: E8507 - one lookup per copied menu, on that menu's own view key
                .sudo()
                .search(
                    [
                        ("key", "=", old_menu.view_id.key),
                        ("website_id", "=?", old_menu.event_id.website_id.id),
                    ],
                    order="write_date DESC",
                    limit=1,
                )
            )
            new_menu.view_id = view.copy(
                {
                    "key": f"{old_menu.view_id.key}-t{int(datetime.now().timestamp())}",
                    "website_id": view.website_id.id,
                }
            )
            self._copy_children_views(
                new_menu.view_id,
                view.inherit_children_ids,
                old_menu.event_id.website_id.id,
            )
            new_url = f"/event/{self.env['ir.http']._slug(new_menu.event_id)}/page/{new_menu.view_id.key.split('.')[-1]}"
            new_menu_defaults = {"url": new_url}

            if old_menu.menu_id.page_id:
                new_page = old_menu.menu_id.page_id.copy({"url": new_url})
                new_menu_defaults["page_id"] = new_page.id

            new_menu.menu_id = old_menu.menu_id.copy(new_menu_defaults)
        return new_menus

    @api.model
    def _copy_children_views(self, new_view, children_views, website_id):
        new_view.check_singleton()
        for child_view in children_views:
            view_info = child_view.key.split(".")
            view = (
                self.env["ir.ui.view"]  # noqa: E8507 - one lookup per child view, on that view's own key
                .sudo()
                .search(
                    [("key", "=", child_view.key), ("website_id", "=?", website_id)],
                    order="write_date DESC",
                    limit=1,
                )
            )
            new_child_view = view.copy(
                {
                    "key": self.env["website"].get_unique_key(
                        view_info[-1], view_info[0]
                    ),
                    "inherit_id": new_view.id,
                    "website_id": view.website_id.id,
                }
            )
            self._copy_children_views(
                new_child_view, view.inherit_children_ids, website_id
            )

    def unlink(self):
        self.view_id.sudo().unlink()
        return super().unlink()
