from urllib.parse import parse_qsl, urlsplit

import werkzeug.exceptions

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools.translate import html_translate

_debug = DebugLog(__name__)


class WebsiteMenu(models.Model):
    _name = "website.menu"

    _description = "Website Menu"

    _parent_store = True
    _order = "sequence, id"

    def _default_sequence(self):
        domain = []
        website_id = self.env.context.get("website_id")
        if website_id:
            domain = [("website_id", "in", (False, website_id))]
        menu = self.search(domain, limit=1, order="sequence DESC")
        return menu.sequence or 0

    @api.depends("mega_menu_content")
    def _compute_is_mega_menu(self):
        for menu in self:
            menu.is_mega_menu = bool(menu.mega_menu_content)

    def _inverse_is_mega_menu(self):
        for menu in self:
            if menu.is_mega_menu:
                if not menu.mega_menu_content:
                    menu.mega_menu_content = self.env["ir.ui.view"]._render_template(
                        "website.s_mega_menu_odoo_menu"
                    )
            else:
                menu.mega_menu_content = False
                menu.mega_menu_classes = False

    name = fields.Char(
        string="Menu",
        translate=True,
        required=True,
    )
    url = fields.Char(
        compute="_compute_url",
        precompute=True,
        store=True,
        copy=True,
        readonly=False,
        required=True,
    )
    page_id = fields.Many2one(
        comodel_name="website.page",
        string="Related Page",
        index="btree_not_null",
        ondelete="cascade",
    )
    controller_page_id = fields.Many2one(
        comodel_name="website.controller.page",
        string="Related Model Page",
        index="btree_not_null",
        ondelete="cascade",
    )
    new_window = fields.Boolean()
    sequence = fields.Integer(default=_default_sequence)
    website_id = fields.Many2one(
        comodel_name="website",
        ondelete="cascade",
    )
    parent_id = fields.Many2one(
        comodel_name="website.menu",
        string="Parent Menu",
        index=True,
        ondelete="cascade",
    )
    child_id = fields.One2many(
        comodel_name="website.menu",
        inverse_name="parent_id",
        string="Child Menus",
    )
    parent_path = fields.Char(index=True)
    is_visible = fields.Boolean(compute="_compute_is_visible")
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Visible Groups",
        groups="base.group_user",
        help="User needs to be at least in one of these groups to see the menu",
    )
    is_mega_menu = fields.Boolean(
        compute=_compute_is_mega_menu,
        inverse=_inverse_is_mega_menu,
    )
    mega_menu_content = fields.Html(
        translate=html_translate,
        sanitize=False,
        prefetch=True,
    )
    mega_menu_classes = fields.Char()

    @api.depends("website_id")
    @api.depends_context("display_website", "uid")
    def _compute_display_name(self):
        if not self.env.context.get("display_website") and not self.env.user.has_group(
            "website.group_multi_website"
        ):
            return super()._compute_display_name()

        for menu in self:
            menu_name = menu.name or ""
            if menu.website_id:
                menu_name += f" [{menu.website_id.name}]"
            menu.display_name = menu_name
        return None

    @api.depends("page_id", "is_mega_menu", "child_id")
    def _compute_url(self):
        for menu in self:
            if menu.is_mega_menu or menu.child_id:
                menu.url = "#"
            else:
                menu.url = (menu.page_id.url if menu.page_id else menu.url) or "#"

    @api.constrains("parent_id", "child_id", "is_mega_menu", "mega_menu_content")
    def _check_parent_menu(self):
        for record in self:
            parent_menu = record.parent_id.sudo() if record.parent_id else None

            level = 0
            current_menu = parent_menu
            while current_menu:
                level += 1
                current_menu = current_menu.parent_id
                if level > 2:
                    _debug.logic(
                        "menu_refused", reason="too_deep", menu=record.id, level=level
                    )
                    raise UserError(
                        _("Menus cannot have more than two levels of hierarchy.")
                    )

            if parent_menu:
                if parent_menu.is_mega_menu or (
                    record.is_mega_menu and (parent_menu.parent_id or record.child_id)
                ):
                    _debug.logic(
                        "menu_refused", reason="mega_menu_nesting", menu=record.id
                    )
                    raise UserError(
                        _("A mega menu cannot have a parent or child menu.")
                    )

                if record.child_id and (
                    parent_menu.parent_id or record.child_id.child_id
                ):
                    _debug.logic(
                        "menu_refused", reason="submenu_with_children", menu=record.id
                    )
                    raise UserError(
                        _("Menus with child menus cannot be added as a submenu.")
                    )

    @api.model_create_multi
    def create(self, vals_list):
        menus = self.env["website.menu"]
        websites = self.env["website"]
        if not self.env.context.get("website_id") and any(
            "website_id" not in vals and vals.get("url") != "/default-main-menu"
            for vals in vals_list
        ):
            websites = websites.search([])
        for vals in vals_list:
            if vals.get("url") == "/default-main-menu":
                menus |= super().create(vals)
                continue
            if "website_id" in vals:
                menus |= super().create(vals)
                continue
            if self.env.context.get("website_id"):
                vals["website_id"] = self.env.context.get("website_id")
                menus |= super().create(vals)
                continue
            default_menu = self.env.ref("website.main_menu", raise_if_not_found=False)
            w_vals = []
            for website in websites:
                parent_id = vals.get("parent_id")
                if not parent_id or (default_menu and parent_id == default_menu.id):
                    parent_id = website.menu_id.id
                w_vals.append(
                    {
                        **vals,
                        "website_id": website.id,
                        "parent_id": parent_id,
                    }
                )
            _debug.logic(
                "menu_create",
                by="fanned_out",
                websites=len(websites),
                url=vals.get("url"),
            )
            new_menu = super().create(w_vals)[-1:]
            if default_menu and vals.get("parent_id") == default_menu.id:
                new_menu = super().create(vals)
            menus |= new_menu
        _debug.lifecycle("create", menus=menus, count=len(menus))
        self.env.registry.clear_cache("templates")
        return menus

    def write(self, vals):
        _debug.lifecycle("write", menus=self, count=len(self), fields=sorted(vals))
        res = super().write(vals)
        if "group_ids" in vals and not self.env.context.get(
            "adding_designer_group_to_menu"
        ):
            restricted = self.filtered("group_ids")
            _debug.lifecycle("menu_designer_group_added", menus=restricted)
            restricted.with_context(
                adding_designer_group_to_menu=True
            ).group_ids += self.env.ref("website.group_website_designer")
        # After the write, not before: a cache cleared ahead of its own change is
        # free to be refilled from pre-change state by anything `super()` reads.
        self.env.registry.clear_cache("templates")
        return res

    def unlink(self):
        default_menu = self.env.ref("website.main_menu", raise_if_not_found=False)
        generic_menus = self.filtered(
            lambda m: (
                default_menu
                and not m.website_id
                and m.parent_id.id == default_menu.id
                and m.url
                and m.url != "#"
            )
        )
        menus_to_remove = self
        if generic_menus:
            menus_to_remove |= self.env["website.menu"].search(
                [
                    ("url", "in", generic_menus.mapped("url")),
                    ("website_id", "!=", False),
                ]
            )
        _debug.lifecycle(
            "unlink",
            menus=self,
            count=len(self),
            generic=len(generic_menus),
            cascaded=len(menus_to_remove) - len(self),
        )
        result = super(WebsiteMenu, menus_to_remove).unlink()
        self.env.registry.clear_cache("templates")
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_tags(self):
        main_menu = self.env.ref("website.main_menu", raise_if_not_found=False)
        if main_menu and main_menu in self:
            _debug.logic("menu_unlink_refused", reason="main_menu")
            raise UserError(
                _(
                    "You cannot delete this website menu as this serves as the default parent menu for new websites (e.g., /shop, /event, ...)."
                )
            )

    @api.depends_context("uid")
    def _compute_is_visible(self):
        for menu in self:
            visible = True
            if menu.page_id and not menu.env.user._is_internal():
                page_sudo = menu.page_id.sudo()
                if not page_sudo.is_visible or (
                    not page_sudo.view_id._handle_visibility(do_raise=False)
                    and page_sudo.view_id._get_cached_visibility() != "password"
                ):
                    visible = False

            if menu.controller_page_id and not menu.env.user._is_internal():
                controller_page_sudo = menu.controller_page_id.sudo()
                if not controller_page_sudo.is_published or (
                    not controller_page_sudo.view_id._handle_visibility(do_raise=False)
                    and controller_page_sudo.view_id._get_cached_visibility()
                    != "password"
                ):
                    visible = False

            menu.is_visible = visible

    def _clean_url(self):
        url = self.url
        if url and not self.url.startswith("/"):
            if "@" in self.url:
                if not self.url.startswith("mailto"):
                    url = "mailto:%s" % self.url
            elif not self.url.startswith("http"):
                url = "/%s" % self.url
        return url

    def _is_active(self):
        if not request or self.is_mega_menu:
            return False

        request_url = urlsplit(request.httprequest.url)

        if not self.child_id:
            menu_url = urlsplit(self._clean_url())
            unslug_url = self.env["ir.http"]._unslug_url
            if unslug_url(menu_url.path) == unslug_url(request_url.path):
                if self.page_id and menu_url.path != request_url.path:
                    return False
                if not (
                    set(parse_qsl(menu_url.query, keep_blank_values=True))
                    <= set(parse_qsl(request_url.query, keep_blank_values=True))
                ):
                    return False
                return not (menu_url.netloc and menu_url.netloc != request_url.netloc)
        elif any(child._is_active() for child in self.child_id):
            return True

        return False

    @api.model
    def get_tree(self, website_id, menu_id=None):
        website = self.env["website"].browse(website_id)

        def prepare_menu_node(node):
            menu_node = {
                "fields": {
                    "id": node.id,
                    "name": node.name,
                    "url": node.url,
                    "new_window": node.new_window,
                    "is_mega_menu": node.is_mega_menu,
                    "sequence": node.sequence,
                    "parent_id": node.parent_id.id,
                },
                "children": [],
                "is_homepage": node.url == (website.homepage_url or "/"),
            }
            for child in node.child_id:
                menu_node["children"].append(prepare_menu_node(child))
            return menu_node

        menu = (menu_id and self.browse(menu_id)) or website.menu_id
        return prepare_menu_node(menu)

    _SAVE_ALLOWED_FIELDS = frozenset(
        {
            "name",
            "url",
            "new_window",
            "is_mega_menu",
            "sequence",
            "parent_id",
            "page_id",
        }
    )

    @api.model
    def save(self, website_id, data):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic("menu_save_refused", reason="not_restricted_editor")
            raise AccessError(_("Only website editors can edit the menus."))
        _debug.pipeline(
            "menu_save",
            website=website_id,
            menus=len(data.get("data") or ()),
            deleted=len(data.get("to_delete") or ()),
        )

        def replace_id(old_id, new_id):
            for menu in data["data"]:
                if menu["id"] == old_id:
                    menu["id"] = new_id
                if menu["parent_id"] == old_id:
                    menu["parent_id"] = new_id

        to_delete = data.get("to_delete")
        if to_delete:
            self.browse(to_delete).unlink()
        for menu in data["data"]:
            mid = menu["id"]
            if isinstance(mid, str):
                new_menu = self.create({"name": menu["name"], "website_id": website_id})
                replace_id(mid, new_menu.id)
        for menu in data["data"]:
            menu_id = self.browse(menu["id"])
            if "#" in menu["url"]:
                if menu_id.page_id:
                    menu_id.page_id = None
                if request and menu["url"].startswith("#") and len(menu["url"]) > 1:
                    referer_url = urlsplit(
                        request.httprequest.headers.get("Referer", "")
                    ).path
                    menu["url"] = referer_url + menu["url"]
            else:
                domain = self.env["website"].browse(website_id).website_domain() & (
                    Domain("url", "=", menu["url"])
                    | Domain("url", "=", "/" + menu["url"])
                )
                page = self.env["website.page"].search(domain, limit=1)  # noqa: E8507 - one probe per submitted menu url; the limit=1 pick follows the website-specific ordering
                if page:
                    _debug.logic("menu_bound", by="page", menu=menu_id.id, page=page.id)
                    menu["page_id"] = page.id
                    menu["url"] = page.url
                    if isinstance(menu.get("parent_id"), str):
                        menu["parent_id"] = int(menu["parent_id"])
                elif menu_id.page_id:
                    try:
                        self.env["ir.http"]._match(menu["url"])
                        _debug.logic(
                            "menu_bound",
                            by="controller",
                            menu=menu_id.id,
                            url=menu["url"],
                        )
                        menu_id.page_id = None
                    except werkzeug.exceptions.NotFound:
                        _debug.logic(
                            "menu_bound",
                            by="page_url_rewritten",
                            menu=menu_id.id,
                            url=menu["url"],
                        )
                        menu_id.page_id.write({"url": menu["url"]})
            menu_id.write(
                {k: v for k, v in menu.items() if k in self._SAVE_ALLOWED_FIELDS}
            )

        return True
