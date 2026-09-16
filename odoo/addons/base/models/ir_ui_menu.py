import base64
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Self

from odoo import _lt, api, fields, models, tools
from odoo.api import ValuesType
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

MENU_ITEM_SEPARATOR = "/"
_MISSING = object()
NUMBER_PARENS = re.compile(r"\((\d+)\)\s*$")


class IrUiMenu(models.Model):
    _name = "ir.ui.menu"
    _inherit = ["mixin.hierarchy"]
    _description = "Menu"
    _order = "sequence,id"
    _allow_sudo_commands = False

    name = fields.Char(
        string="Menu",
        translate=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    parent_id = fields.Many2one(
        comodel_name="ir.ui.menu",
        string="Parent Menu",
        index=True,
        ondelete="restrict",
    )
    child_id = fields.One2many(
        comodel_name="ir.ui.menu",
        inverse_name="parent_id",
        string="Child IDs",
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="ir_ui_menu_group_rel",
        column1="menu_id",
        column2="gid",
        string="Groups",
        help="If you have groups, the visibility of this menu will be based on these groups. "
        "If this field is empty, Odoo will compute visibility based on the related object's read access.",
    )
    complete_name = fields.Char(
        string="Full Path",
        compute="_compute_complete_name",
        recursive=True,
    )
    web_icon = fields.Char(string="Web Icon File")
    web_keywords = fields.Char(
        string="Search Keywords",
        translate=True,
        help="Comma-separated words the app launcher matches this menu on, "
        "beyond its name: the vocabulary users type but the menu is not called, "
        'such as "invoice, bill" for Accounting.',
    )
    action = fields.Reference(
        selection=[
            ("ir.actions.report", "ir.actions.report"),
            ("ir.actions.act_window", "ir.actions.act_window"),
            ("ir.actions.act_url", "ir.actions.act_url"),
            ("ir.actions.server", "ir.actions.server"),
            ("ir.actions.client", "ir.actions.client"),
        ]
    )

    web_icon_data = fields.Binary(
        string="Web Icon Image",
        attachment=True,
    )

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self) -> None:
        self._update_full_name("complete_name")

    def _update_full_name(self, fname: str) -> None:
        for menu in self:
            if menu.parent_id:
                menu[fname] = (
                    (menu.parent_id[fname] or "")
                    + MENU_ITEM_SEPARATOR
                    + (menu.name or "")
                )
            else:
                menu[fname] = menu.name

    def _read_image(self, path: str) -> bytes | bool:
        if not path:
            return False
        path_info = path.split(",")
        if len(path_info) != 2:
            _debug.logic("web_icon_skipped", parts=len(path_info))
            return False
        icon_path = str(Path(path_info[0]) / path_info[1])
        try:
            with tools.file_open(
                icon_path,
                "rb",
                filter_ext=(
                    ".png",
                    ".gif",
                    ".ico",
                    ".jfif",
                    ".jpeg",
                    ".jpg",
                    ".svg",
                    ".webp",
                ),
            ) as icon_file:
                return base64.encodebytes(icon_file.read())
        except FileNotFoundError, ValueError:
            _debug.logic("web_icon_unreadable", path=icon_path)
            return False

    _hierarchy_cycle_message = _lt("Error! You cannot create recursive menus.")

    @api.model
    @tools.ormcache("frozenset(self.env.user._get_group_ids())", "debug")
    def _get_visible_menu_ids(self, debug: bool = False) -> frozenset[int]:
        group_ids = set(self.env.user._get_group_ids())
        if not debug:
            group_ids.discard(
                self.env["ir.model.data"]._xmlid_to_res_id(
                    "base.group_no_one", raise_if_not_found=False
                )
            )

        menus = (
            self.with_context({})
            .search_fetch(
                [
                    "|",
                    ("group_ids", "=", False),
                    ("group_ids", "in", tuple(group_ids)),
                ],
                ["parent_id", "action"],
                order="id",
            )
            .sudo()
        )

        action_ids_by_model = defaultdict(list)
        for action in menus.mapped("action"):
            if action:
                action_ids_by_model[action._name].append(action.id)

        actions = self.env["ir.actions.actions"]
        MODEL_BY_TYPE = {
            model_name: field_name
            for model_name in actions._get_model_names_in_tree()
            if (field_name := self.env[model_name]._get_field_target_model())
        }

        def exists_actions(model_name, action_ids):
            if model_name not in MODEL_BY_TYPE:
                return self.env[model_name].browse(action_ids).exists()
            field_name = MODEL_BY_TYPE[model_name]
            records = (
                self.env[model_name]
                .sudo()
                .with_context(active_test=False)
                .search_fetch(
                    [("id", "in", action_ids)],
                    [field_name],
                    order="id",
                )
            )
            records.mapped(field_name)
            return records

        existing_actions = {
            action
            for model_name, action_ids in action_ids_by_model.items()
            for action in exists_actions(model_name, action_ids)
        }
        _debug.perf.count(
            "menu_actions_checked",
            action_models=len(action_ids_by_model),
            referenced=sum(len(ids) for ids in action_ids_by_model.values()),
            existing=len(existing_actions),
        )
        menu_ids = set(menus._ids)
        visible_ids = set()
        access = self.env["ir.model.access"]
        no_action = access_denied = 0  # debuglog
        for menu in menus:
            action = menu.action
            if not action or action not in existing_actions:
                no_action += 1  # debuglog
                continue
            model_fname = MODEL_BY_TYPE.get(action._name)
            gating_model = action[model_fname] if model_fname else None
            if gating_model and not access.check(gating_model, "read", False):
                access_denied += 1  # debuglog
                continue
            menu_id = menu.id
            while menu_id not in visible_ids and menu_id in menu_ids:
                visible_ids.add(menu_id)
                menu = menu.parent_id
                menu_id = menu.id

        _debug.perf.count(
            "visible_menus_computed",
            uid=self.env.uid,
            debug=debug,
            candidates=len(menus),
            visible=len(visible_ids),
            no_action=no_action,
            access_denied=access_denied,
        )
        return frozenset(visible_ids)

    def _filter_visible_menus(self, debug: str | bool | None = None) -> Self:
        if debug is None:
            debug = self._get_session_debug()
        visible_ids = self._get_visible_menu_ids(debug)
        visible = self.filtered(lambda menu: menu.id in visible_ids)
        _debug.logic("menus_filtered", candidates=len(self), visible=len(visible))
        return visible

    @api.depends("complete_name")
    def _compute_display_name(self) -> None:
        for menu in self:
            menu.display_name = menu.complete_name

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        if not vals_list:
            return self.browse()
        _debug.lifecycle("create", count=len(vals_list))
        self.env.registry.clear_cache()
        return super().create(
            [
                {**values, "web_icon_data": self._prepare_web_icon_data(icon)}
                if (icon := values.get("web_icon", _MISSING)) is not _MISSING
                else values
                for values in vals_list
            ]
        )

    def write(self, vals: dict[str, Any]) -> bool:
        if self and vals:
            _debug.lifecycle("write", count=len(self), fields=list(vals))
            self.env.registry.clear_cache()
        if "web_icon" in vals:
            vals = {
                **vals,
                "web_icon_data": self._prepare_web_icon_data(vals.get("web_icon")),
            }
            _debug.lifecycle(
                "web_icon_refreshed",
                count=len(self),
                loaded=bool(vals["web_icon_data"]),
            )
        return super().write(vals)

    def _prepare_web_icon_data(self, web_icon: str | None) -> bytes | bool:
        if web_icon and len(web_icon.split(",")) == 2:
            return self._read_image(web_icon)
        return False

    def unlink(self) -> bool:
        if not self:
            return True
        direct_children = self.with_context(active_test=False).search(
            [("parent_id", "in", self.ids)]
        )
        _debug.lifecycle(
            "unlink.children_detached", count=len(self), children=len(direct_children)
        )
        direct_children.write({"parent_id": False})

        _debug.lifecycle("unlink", count=len(self), orphaned=len(direct_children))
        self.env.registry.clear_cache()
        return super().unlink()

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        vals_list = super().copy_data(default=default)
        renamed = 0  # debuglog
        for vals in vals_list:
            if name := vals.get("name"):
                renamed += 1  # debuglog
                if match := NUMBER_PARENS.search(name):
                    next_num = int(match.group(1)) + 1
                    vals["name"] = NUMBER_PARENS.sub(f"({next_num})", name, count=1)
                else:
                    vals["name"] = name + " (1)"
        _debug.lifecycle("copy_data", count=len(self), renamed=renamed)
        return vals_list

    @api.model
    def get_user_roots(self) -> Self:
        return self.search([("parent_id", "=", False)])._filter_visible_menus()

    def _get_blacklisted_menu_ids(self) -> list[int]:
        return []

    def _get_session_debug(self) -> str | bool:
        return request.session.debug if request else False

    @api.model
    @tools.ormcache("self.env.uid", "self.env.lang", "self._get_session_debug()")
    def load_menus_root(self) -> dict[str, Any]:
        fields = ["name", "sequence", "parent_id", "action", "web_icon_data"]
        menu_roots = self.get_user_roots()
        menu_roots_data = menu_roots.read(fields) if menu_roots else []

        menu_root = {
            "id": False,
            "name": "root",
            "parent_id": [-1, ""],
            "children": menu_roots_data,
            "all_menu_ids": menu_roots.ids,
        }

        xmlids = menu_roots._get_menuitems_xmlids()
        for menu in menu_roots_data:
            menu["xmlid"] = xmlids.get(menu["id"], "")

        _debug.pipeline("load_menus_root", uid=self.env.uid, roots=len(menu_roots))
        return menu_root

    @api.model
    @tools.ormcache("self.env.uid", "debug", "self.env.lang")
    def load_menus(self, debug: bool) -> dict[str | int, Any]:
        blacklisted_menu_ids = self._get_blacklisted_menu_ids()
        with _debug.perf(
            "load_menus.fetch",
            cr=self.env.cr,
            uid=self.env.uid,
            blacklisted=len(blacklisted_menu_ids),
        ):
            visible_menus = self.search_fetch(
                [("id", "not in", blacklisted_menu_ids)],
                ["name", "parent_id", "action", "web_icon", "web_keywords"],
            )._filter_visible_menus(debug)

        children_dict = defaultdict(list)
        for menu in visible_menus:
            children_dict[menu.parent_id.id].append(menu.id)

        app_info = self._get_app_id_by_menu(children_dict)
        reachable = len(visible_menus)  # debuglog
        visible_menus = visible_menus.filtered(lambda menu: menu.id in app_info)
        _debug.pipeline(
            "load_menus",
            uid=self.env.uid,
            debug=debug,
            reachable=reachable,
            visible=len(visible_menus),
            apps=len(children_dict[False]),
        )

        xmlids = visible_menus._get_menuitems_xmlids()
        icons_by_menu = self._get_menu_icons(visible_menus)

        menus_dict = {}
        action_ids_by_type = defaultdict(list)
        for menu in visible_menus:
            menu_id = menu.id
            attachment = icons_by_menu.get(menu_id)

            if action := menu.action:
                action_model = action._name
                action_id = action.id
                action_ids_by_type[action_model].append(action_id)
            else:
                action_model = False
                action_id = False

            menus_dict[menu_id] = {
                "id": menu_id,
                "name": menu.name,
                "app_id": app_info[menu_id],
                "action_model": action_model,
                "action_id": action_id,
                "web_icon": menu.web_icon,
                "web_keywords": menu.web_keywords,
                "web_category": False,
                "web_category_sequence": 0,
                "web_icon_data": (
                    attachment["datas"].decode()
                    if attachment and attachment["datas"]
                    else False
                ),
                "web_icon_data_mimetype": (
                    attachment["mimetype"] if attachment else False
                ),
                "xmlid": xmlids.get(menu_id, ""),
            }

        action_info_by_action = self._get_action_info(action_ids_by_type)

        for menu_dict in menus_dict.values():
            info = action_info_by_action.get(
                (menu_dict["action_model"], menu_dict["action_id"])
            )
            menu_dict["action_path"] = info["path"] if info else False
            menu_dict["action_res_model"] = info["res_model"] if info else False
            menu_dict["children"] = children_dict[menu_dict["id"]]

        for menu_id, (category, sequence) in self._get_app_categories(
            children_dict[False], menus_dict
        ).items():
            menus_dict[menu_id]["web_category"] = category
            menus_dict[menu_id]["web_category_sequence"] = sequence
        _debug.pipeline(
            "load_menus.built",
            uid=self.env.uid,
            menus=len(menus_dict),
            action_types=len(action_ids_by_type),
            actions=len(action_info_by_action),
        )

        menus_dict["root"] = {
            "id": False,
            "name": "root",
            "children": children_dict[False],
        }
        return menus_dict

    def _get_app_categories(
        self, root_menu_ids: list[int], menus_dict: dict
    ) -> dict[int, tuple[str, int]]:
        """Group heading for each app, and the order its group sits in.

        The heading is the top of the module's category tree. The leaf category
        is very nearly the app itself -- measured over a 22-app database it
        yields 17 categories, 12 of them holding one app, so it names more
        groups than it saves rows. Its root names eight, of sizes that read:
        Sales, Supply Chain, Productivity, Accounting.

        The sequence travels with the name because the client has no other way
        to order the groups. Menus are ordered by their own sequence, so
        grouping them alone puts the headings in the order the first app of
        each happens to appear -- Productivity before Sales because Calendar
        outranks CRM. `ir.module.category.sequence` is the field that already
        answers this, and it is the same order the Apps store and the
        access-rights page use.
        """
        modules_by_menu = {}
        for menu_id in root_menu_ids:
            module = (menus_dict.get(menu_id, {}).get("xmlid") or "").split(".")[0]
            if module:
                modules_by_menu[menu_id] = module
        if not modules_by_menu:
            _debug.logic("app_categories_skipped", roots=len(root_menu_ids))
            return {}
        # sudo: an app's heading is not the reader's business to have rights on
        modules = (
            self.env["ir.module.module"]
            .sudo()
            .search_fetch(
                [("name", "in", list(set(modules_by_menu.values())))],
                ["name", "category_id"],
            )
        )
        category_by_module = {module.name: module.category_id for module in modules}
        categories = {}
        for menu_id, module_name in modules_by_menu.items():
            category = category_by_module.get(module_name)
            while category and category.parent_id:
                category = category.parent_id
            if category:
                categories[menu_id] = (category.name, category.sequence)
        _debug.perf.count(
            "app_categories_computed",
            roots=len(root_menu_ids),
            modules=len(modules),
            headings=len({name for name, _seq in categories.values()}),
        )
        return categories

    @classmethod
    def _get_app_id_by_menu(cls, children_dict: dict) -> dict[int, int]:
        app_info: dict[int, int] = {}
        for root_menu_id in children_dict[False]:
            cls._update_app_id(app_info, children_dict, root_menu_id, root_menu_id)
        _debug.perf.count(
            "app_ids_assigned", apps=len(children_dict[False]), menus=len(app_info)
        )
        return app_info

    @classmethod
    def _update_app_id(
        cls, app_info: dict, children_dict: dict, menu_app_id: int, menu_id: int
    ) -> None:
        if menu_id in app_info:
            return
        app_info[menu_id] = menu_app_id
        for child_id in children_dict[menu_id]:
            cls._update_app_id(app_info, children_dict, menu_app_id, child_id)

    def _get_menu_icons(self, visible_menus: Any) -> dict[int, dict]:
        icon_attachments = (
            self.env["ir.attachment"]
            .sudo()
            .search_read(
                domain=[
                    ("res_model", "=", "ir.ui.menu"),
                    ("res_id", "in", visible_menus._ids),
                    ("res_field", "=", "web_icon_data"),
                ],
                fields=["res_id", "datas", "mimetype"],
            )
        )
        _debug.perf.count(
            "menu_icons_loaded", menus=len(visible_menus), icons=len(icon_attachments)
        )
        return {attachment["res_id"]: attachment for attachment in icon_attachments}

    def _get_action_info(self, action_ids_by_type: dict) -> dict[tuple, dict[str, Any]]:
        action_info_by_action = {}
        for model_name, action_ids in action_ids_by_type.items():
            actions = self.env[model_name].sudo().browse(action_ids)
            has_res_model = "res_model" in actions._fields
            actions.fetch(["path", "res_model"] if has_res_model else ["path"])
            for action in actions:
                action_info_by_action[model_name, action.id] = {
                    "path": action.path,
                    "res_model": action.res_model if has_res_model else False,
                }
        _debug.perf.count(
            "menu_actions_loaded",
            types=len(action_ids_by_type),
            actions=len(action_info_by_action),
        )
        return action_info_by_action

    def _get_menuitems_xmlids(self) -> dict[int, str]:
        menuitems = (
            self.env["ir.model.data"]
            .sudo()
            .search_fetch(
                [("res_id", "in", self.ids), ("model", "=", "ir.ui.menu")],
                ["res_id", "complete_name"],
            )
        )
        _debug.perf.count("menu_xmlids_loaded", menus=len(self), xmlids=len(menuitems))
        return {menu.res_id: menu.complete_name for menu in menuitems}
