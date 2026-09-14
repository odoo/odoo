import logging
from typing import TYPE_CHECKING, Any

from lxml import etree
from lxml.builder import E

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import _, config, frozendict
from odoo.tools.view_ir import from_arch, from_string

from .ir_ui_view import _xpath_descendant_field

if TYPE_CHECKING:
    from lxml.etree import _Element

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def attach_ir(result: dict[str, Any]) -> dict[str, Any]:
    """Derive ``result["ir"]`` from ``result["arch"]`` again.

    A view payload carries the arch twice — the string and the IR the
    client reads first. An override that rewrites ``arch`` after
    ``get_view`` (a js_class added on the fly, a field name substituted)
    must hand the result through here, or the client renders the tree the
    override never touched.
    """
    result["ir"] = from_string(result["arch"]).to_dict()
    return result


class Base(models.AbstractModel):
    _inherit = "base"

    _date_name = "date"

    def _get_access_action(
        self, access_uid: int | None = None, force_website: bool = False
    ) -> dict[str, Any]:
        self.check_singleton()
        return self.get_formview_action(access_uid=access_uid)

    @api.model
    def get_empty_list_help(self, help_message: str) -> str:
        return help_message

    @api.model
    def view_header_get(self, view_id: int | None, view_type: str) -> str | bool:
        return False

    @api.model
    def _get_default_form_view(self) -> _Element:
        sheet = E.sheet(string=self._description)
        main_group = E.group()
        left_group = E.group()
        right_group = E.group()
        for fname, field in self._fields.items():
            if (
                fname in models.MAGIC_COLUMNS
                or (fname == "display_name" and field.readonly)
                or (
                    field.type == "binary"
                    and not isinstance(field, fields.Image)
                    and not field.store
                )
            ):
                continue
            if field.type in ("one2many", "many2many", "text", "html"):
                if len(left_group) > 0:
                    main_group.append(left_group)
                    left_group = E.group()
                if len(right_group) > 0:
                    main_group.append(right_group)
                    right_group = E.group()
                if len(main_group) > 0:
                    sheet.append(main_group)
                    main_group = E.group()
                sheet.append(E.group(E.field(name=fname)))
            elif len(left_group) > len(right_group):
                right_group.append(E.field(name=fname))
            else:
                left_group.append(E.field(name=fname))
        if len(left_group) > 0:
            main_group.append(left_group)
        if len(right_group) > 0:
            main_group.append(right_group)
        sheet.append(main_group)
        sheet.append(E.group(E.separator()))
        return E.form(sheet)

    @api.model
    def _get_default_search_view(self) -> _Element:
        element = E.field(name=self._get_rec_name_fallback())
        return E.search(element, string=self._description)

    @api.model
    def _get_default_list_view(self) -> _Element:
        element = E.field(name=self._get_rec_name_fallback())
        return E.list(element, string=self._description)

    @api.model
    def _get_default_pivot_view(self) -> _Element:
        return E.pivot(string=self._description)

    @api.model
    def _get_default_kanban_view(self) -> _Element:

        field = E.field(name=self._get_rec_name_fallback())
        kanban_card = E.t(field, {"t-name": "card"})
        templates = E.templates(kanban_card)
        return E.kanban(templates, string=self._description)

    @api.model
    def _get_default_graph_view(self) -> _Element:
        element = E.field(name=self._get_rec_name_fallback())
        return E.graph(element, string=self._description)

    @api.model
    def _get_default_calendar_view(self) -> _Element:

        def set_first_of(seq: list[str], in_: dict, to: str) -> bool:
            for item in seq:
                if item in in_ and in_[item]._description_searchable:
                    view.set(to, item)
                    return True
            return False

        view = E.calendar(string=self._description)
        view.append(E.field(name=self._get_rec_name_fallback()))

        if not set_first_of(
            [self._date_name, "date", "date_start", "x_date", "x_date_start"],
            self._fields,
            "date_start",
        ):
            _debug.logic(
                "default_calendar_refused", model=self._name, missing="date_start"
            )
            raise UserError(_("Insufficient fields for Calendar View!"))

        set_first_of(
            ["user_id", "partner_id", "x_user_id", "x_partner_id"],
            self._fields,
            "color",
        )

        if not set_first_of(
            ["date_stop", "date_end", "x_date_stop", "x_date_end"],
            self._fields,
            "date_stop",
        ):
            if not set_first_of(
                [
                    "date_delay",
                    "planned_hours",
                    "x_date_delay",
                    "x_planned_hours",
                ],
                self._fields,
                "date_delay",
            ):
                _debug.logic(
                    "default_calendar_refused", model=self._name, missing="date_stop"
                )
                raise UserError(
                    _(
                        "Insufficient fields to generate a Calendar View for %s, missing a date_stop or a date_delay",
                        self._name,
                    )
                )

        _debug.logic(
            "default_calendar_view",
            model=self._name,
            date_start=view.get("date_start"),
            date_stop=view.get("date_stop"),
            date_delay=view.get("date_delay"),
            color=view.get("color"),
        )
        return view

    @api.model
    @api.readonly
    def get_views(
        self,
        views: list[list[int | str]],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        options = options or {}
        result = {}

        with _debug.perf(
            "get_views",
            cr=self.env.cr,
            model=self._name,
            views=[v_type for _v_id, v_type in views],
            toolbar=bool(options.get("toolbar")),
        ):
            result["views"] = {
                v_type: self.get_view(v_id, v_type, **options)
                for [v_id, v_type] in views
            }

        view_models = {}
        for view in result["views"].values():
            for model, model_fields in view.pop("models").items():
                view_models.setdefault(model, set()).update(model_fields)

        result["models"] = {}

        for model, model_fields in view_models.items():
            result["models"][model] = {
                "fields": self.env[model].fields_get(
                    allfields=model_fields,
                    attributes=self._get_view_field_attributes(),
                )
            }

        if options.get("toolbar"):
            for view in result["views"].values():
                view["toolbar"] = {}

            bindings = self.env["ir.actions.actions"].get_bindings(self._name)
            for action_type, key in (("report", "print"), ("action", "action")):
                for action in bindings.get(action_type, []):
                    view_types = (
                        action["binding_view_types"].split(",")
                        if action.get("binding_view_types")
                        else result["views"].keys()
                    )
                    for view_type in view_types:
                        if view_type in result["views"]:
                            result["views"][view_type]["toolbar"].setdefault(
                                key, []
                            ).append(action)

        if options.get("load_filters") and "search" in result["views"]:
            result["views"]["search"]["filters"] = self.env["ir.filters"].get_filters(
                self._name,
                options.get("action_id"),
                options.get("embedded_action_id"),
                options.get("embedded_parent_res_id"),
            )

        return result

    @api.model
    def _get_view(
        self,
        view_id: int | None = None,
        view_type: str = "form",
        **options: Any,
    ) -> tuple[_Element, Any]:
        IrUiView = self.env["ir.ui.view"].sudo()

        if not view_id:
            view_ref_key = view_type + "_view_ref"
            view_ref = self.env.context.get(view_ref_key)
            if view_ref:
                if "." in view_ref:
                    ref_model, ref_res_id = self.env[
                        "ir.model.data"
                    ]._xmlid_to_res_model_res_id(view_ref, raise_if_not_found=False)
                    if ref_model == "ir.ui.view":
                        view_id = ref_res_id
                    elif ref_model:
                        _logger.warning(
                            "%r=%r for model %s refers to a %s record, not an "
                            "ir.ui.view; falling back on the default view.",
                            view_ref_key,
                            view_ref,
                            self._name,
                            ref_model,
                        )
                    else:
                        _logger.warning(
                            "%r=%r for model %s does not match any record; "
                            "falling back on the default view.",
                            view_ref_key,
                            view_ref,
                            self._name,
                        )
                else:
                    _logger.warning(
                        "%r requires a fully-qualified external id (got: %r for model %s). "
                        "Please use the complete `module.view_id` form instead.",
                        view_ref_key,
                        view_ref,
                        self._name,
                    )

            if not view_id:
                view_id = IrUiView.default_view(self._name, view_type)

        _debug.logic(
            "view_resolved",
            model=self._name,
            type=view_type,
            view=view_id or None,
            source="record" if view_id else "default",
        )
        if view_id:
            view = IrUiView.browse(view_id)
            arch = view._get_combined_arch()
        else:
            view = IrUiView.browse()
            method = getattr(self, f"_get_default_{view_type}_view", None)
            if method is None:
                raise UserError(
                    _("No default view of type '%s' could be found!", view_type)
                )
            arch = method()
        return arch, view

    def _get_view_postprocessed(
        self, view: Any, arch: _Element, **options: Any
    ) -> tuple[str, dict[str, set[str]]]:
        return view.postprocess_and_fields(arch, model=self._name, **options)

    @api.model
    def _get_view_cache_key(
        self,
        view_id: int | None = None,
        view_type: str = "form",
        **options: Any,
    ) -> tuple:
        return (
            view_id,
            view_type,
            options.get("mobile"),
            self.env.lang,
        ) + tuple(
            sorted(
                (key, value)
                for key, value in self.env.context.items()
                if key.endswith("_view_ref")
            )
        )

    @api.model
    @tools.conditional(
        "xml" not in config["dev_mode"],
        tools.ormcache(
            "self._get_view_cache_key(view_id, view_type, **options)",
            cache="templates",
        ),
    )
    def _get_view_cache(
        self,
        view_id: int | None = None,
        view_type: str = "form",
        **options: Any,
    ) -> frozendict:
        with _debug.perf(
            "view_cache_miss", cr=self.env.cr, model=self._name, type=view_type
        ):
            arch, view = self._get_view(view_id, view_type, **options)
            arch, view_models = self._get_view_postprocessed(view, arch, **options)
            view_models = self._get_fields_view(view_type or view.type, view_models)
        result = {
            "arch": arch,
            "id": view.id,
            "model": self._name,
            "models": frozendict(
                {model: tuple(fields) for model, fields in view_models.items()}
            ),
        }

        return frozendict(result)

    @api.model
    @api.readonly
    def get_view(
        self,
        view_id: int | None = None,
        view_type: str = "form",
        **options: Any,
    ) -> dict[str, Any]:
        self.browse().check_access("read")

        result = dict(self._get_view_cache(view_id, view_type, **options))

        node = etree.fromstring(result["arch"])
        node = self.env["ir.ui.view"]._postprocess_access_rights(node)
        node = self.env["ir.ui.view"]._postprocess_debug(node)
        if node.tag in ("form", "list") and (
            header := self.view_header_get(result["id"], node.tag)
        ):
            node.set("string", header)
        result["arch"] = etree.tostring(node, encoding="unicode")
        with _debug.perf("ir_build", model=self._name, view_type=node.tag) as span:
            ir = from_arch(node)
            result["ir"] = ir.to_dict()
            if _debug.perf.enabled:
                span.set(nodes=sum(1 for _ in ir.walk()))
        _debug.pipeline(
            "get_view",
            model=self._name,
            view=result["id"],
            view_type=node.tag,
            arch_chars=len(result["arch"]),
        )

        return result

    @api.model
    def _get_fields_view(
        self, view_type: str, view_models: dict[str, Any]
    ) -> dict[str, Any]:
        match view_type:
            case "kanban" | "list" | "form":
                for model, model_fields in view_models.items():
                    model_fields.add("id")
                    if "write_date" in self.env[model]._fields:
                        model_fields.add("write_date")
            case "search":
                view_models[self._name] = set(self._fields)
            case "graph":
                view_models[self._name].update(
                    fname
                    for fname, field in self._fields.items()
                    if field.type in ("integer", "float", "monetary")
                )
            case "pivot":
                view_models[self._name].update(
                    fname
                    for fname, field in self._fields.items()
                    if field._description_groupable(self.env)
                )
        return view_models

    @api.model
    def _get_view_field_attributes(self) -> list[str]:
        return [
            "change_default",
            "context",
            "currency_field",
            "definition_record",
            "definition_record_field",
            "digits",
            "min_display_digits",
            "domain",
            "aggregator",
            "groups",
            "help",
            "model_field",
            "name",
            "readonly",
            "related",
            "relation",
            "relation_field",
            "required",
            "searchable",
            "selection",
            "size",
            "sortable",
            "store",
            "string",
            "translate",
            "trim",
            "type",
            "groupable",
            "falsy_value_label",
        ]

    @api.readonly
    def get_formview_id(self, access_uid: int | None = None) -> int | bool:
        return False

    @api.readonly
    def get_formview_action(self, access_uid: int | None = None) -> dict[str, Any]:
        view_id = self.sudo().get_formview_id(access_uid=access_uid)
        _debug.logic("formview_action", model=self._name, record=self.id, view=view_id)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "views": [(view_id, "form")],
            "target": "current",
            "res_id": self.id,
            "context": dict(self.env.context),
        }

    def _get_records_action(self, **kwargs: Any) -> dict[str, Any]:
        match self.ids:
            case []:
                length_dependent = {"views": [(False, "form")]}
            case [res_id]:
                length_dependent = {
                    "views": [(False, "form")],
                    "res_id": res_id,
                }
            case ids:
                length_dependent = {
                    "views": [(False, "list"), (False, "form")],
                    "domain": [("id", "in", ids)],
                }
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "target": "current",
            "context": dict(self.env.context),
            **length_dependent,
            **kwargs,
        }

    @api.model
    def _get_onchange_spec(
        self, view_info: dict[str, Any] | None = None
    ) -> dict[str, str | None]:
        result = {}

        def process(node: _Element, info: dict[str, Any] | None, prefix: str) -> None:
            if node.tag == "field":
                name = node.attrib["name"]
                names = f"{prefix}.{name}" if prefix else name
                if not result.get(names):
                    result[names] = node.attrib.get("on_change")
                for child_view in _xpath_descendant_field(node):
                    process(child_view, None, names)
            else:
                for child in node:
                    process(child, info, prefix)

        if view_info is None:
            view_info = self.get_view()
        process(etree.fromstring(view_info["arch"]), view_info, "")
        return result

    @api.model
    def _get_fields_spec(
        self, view_info: dict[str, Any] | None = None
    ) -> dict[str, Any]:

        def update_spec(
            node: _Element, model: Any, fields_spec: dict[str, Any]
        ) -> None:
            if node.tag == "field":
                field_name = node.attrib["name"]
                field_spec = fields_spec.setdefault(field_name, {})
                field = model._fields.get(field_name)
                if field is not None:
                    sub_fields_spec = {}
                    if field.type == "many2one":
                        sub_fields_spec.setdefault("display_name", {})
                    if field.relational:
                        comodel = model.env[field.comodel_name]
                        for child in node:
                            update_spec(child, comodel, sub_fields_spec)
                    if field.type == "one2many":
                        sub_fields_spec.pop(field.inverse_name, None)
                    if sub_fields_spec:
                        field_spec.setdefault("fields", {}).update(sub_fields_spec)
            else:
                for child in node:
                    update_spec(child, model, fields_spec)

        if view_info is None:
            view_info = self.get_view()

        result = {}
        update_spec(etree.fromstring(view_info["arch"]), self, result)
        return result
