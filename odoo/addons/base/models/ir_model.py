import logging
import re
from collections import defaultdict
from collections.abc import Callable
from typing import Any, Self, override

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.db import schema as sql
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, OrderedSet, remove_accents, unique
from odoo.tools.translate import _

from .ir_model_common import (
    MODULE_UNINSTALL_FLAG,
    compute_modules,
    inherit_xmlid,
    mark_modified,
    model_xmlid,
    reload_schema,
    select_en,
    upsert_en,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

MANUAL_CLASS_MUTABLE_FIELDS = ("name", "order", "info", "fold_name")


class Base(models.AbstractModel):
    _name = "base"
    _description = "Base"


class Unknown(models.AbstractModel):
    _name = "_unknown"
    _description = "Unknown"


class IrModel(models.Model):
    _name = "ir.model"
    _is_registry_metadata = True
    _description = "Models"
    _order = "model"
    _rec_names_search = ["name", "model"]
    _allow_sudo_commands = False

    def _default_field_id(self) -> list[tuple[int, int, dict[str, Any]]]:
        if self.env.context.get("install_mode"):
            return []
        return [
            Command.create(
                {
                    "name": "x_name",
                    "field_description": "Name",
                    "ttype": "char",
                    "copied": True,
                }
            )
        ]

    name = fields.Char(
        string="Model Description",
        translate=True,
        required=True,
    )
    model = fields.Char(
        default="x_",
        required=True,
    )
    order = fields.Char(
        default="id",
        required=True,
        help='SQL expression for ordering records in the model; e.g. "x_sequence asc, id desc"',
    )
    info = fields.Text(string="Information")
    field_id = fields.One2many(
        comodel_name="ir.model.fields",
        inverse_name="model_id",
        string="Fields",
        default=_default_field_id,
        copy=True,
        required=True,
    )
    inherited_model_ids = fields.Many2many(
        comodel_name="ir.model",
        string="Inherited models",
        compute="_compute_inherited_model_ids",
        help="The parent models this model delegates to (via _inherits).",
    )
    state = fields.Selection(
        selection=[("manual", "Custom Object"), ("base", "Base Object")],
        string="Type",
        default="manual",
        readonly=True,
    )
    access_ids = fields.One2many(
        comodel_name="ir.model.access",
        inverse_name="model_id",
    )
    rule_ids = fields.One2many(
        comodel_name="ir.rule",
        inverse_name="model_id",
        string="Record Rules",
    )
    abstract = fields.Boolean(string="Abstract Model")
    transient = fields.Boolean(string="Transient Model")
    modules = fields.Char(
        string="In Apps",
        compute="_compute_modules",
        help="List of modules in which the object is defined or inherited",
    )
    view_ids = fields.One2many(
        comodel_name="ir.ui.view",
        string="Views",
        compute="_compute_view_ids",
    )
    count = fields.Integer(
        string="Count (Incl. Archived)",
        compute="_compute_count",
        help="Total number of records in this model",
    )
    fold_name = fields.Char(
        string="Fold Field",
        help="In a Kanban view where columns are records of this model, the value "
        "of this (boolean) field determines which column should be folded by default.",
    )

    @api.depends()
    def _compute_inherited_model_ids(self) -> None:
        self.inherited_model_ids = False
        all_parent_names: set[str] = set()
        inherits_by_model: dict[str, list[str]] = {}
        for model in self:
            if (records := self.env.get(model.model)) is not None:
                parent_names: list[str] = list(records._inherits)
                if parent_names:
                    inherits_by_model[model.model] = parent_names
                    all_parent_names.update(parent_names)
        if not all_parent_names:
            return
        parent_records = {
            rec.model: rec
            for rec in self.search([("model", "in", list(all_parent_names))])
        }
        _debug.perf.count(
            "inherited_models.resolved",
            models=len(inherits_by_model),
            parents=len(parent_records),
        )
        for model in self:
            if parents := inherits_by_model.get(model.model):
                model.inherited_model_ids = self.browse(
                    parent_records[name].id
                    for name in parents
                    if name in parent_records
                )

    @api.depends()
    def _compute_modules(self) -> None:
        compute_modules(self)

    @api.depends()
    def _compute_view_ids(self) -> None:
        model_names = [m.model for m in self]
        View = self.env["ir.ui.view"]
        views_by_model: dict[str, list[int]] = defaultdict(list)
        if model_names:
            for view in View.search([("model", "in", model_names)]):
                views_by_model[view.model].append(view.id)
        _debug.perf.count(
            "view_ids.collected",
            models=len(model_names),
            with_views=len(views_by_model),
        )
        for model in self:
            model.view_ids = View.browse(views_by_model.get(model.model, []))

    @api.depends()
    def _compute_count(self) -> None:
        self.count = 0
        table_models: list[tuple[str, str]] = [
            (records._table, model.model)
            for model in self
            if (records := self.env.get(model.model)) is not None
            and not records._abstract
            and records._auto
        ]
        if not table_models:
            return
        existing = {
            row[0]
            for row in self.env.execute_query(
                SQL(
                    "SELECT relname FROM pg_class"
                    " WHERE relname = ANY(%s)"
                    " AND relnamespace = current_schema::regnamespace",
                    [table for table, _model_name in table_models],
                )
            )
        }
        parts = [
            SQL(
                "SELECT %s AS model, COUNT(*) FROM %s",
                model_name,
                SQL.identifier(table),
            )
            for table, model_name in table_models
            if table in existing
        ]
        if not parts:
            _debug.logic("count.skipped", models=len(table_models), reason="no_table")
            return
        query = SQL(" UNION ALL ").join(parts)
        with _debug.perf("count.query", cr=self.env.cr, tables=len(parts)):
            counts = dict(self.env.execute_query(query))
        for model in self:
            if model.model in counts:
                model.count = counts[model.model]

    @api.constrains("model")
    def _check_model_name(self) -> None:
        for model in self:
            if model.state == "manual":
                self._check_manual_name(model.model)
            if not models.is_valid_object_name(model.model):
                _debug.logic(
                    "constraint.rejected", model=model.model, reason="invalid_name"
                )
                raise ValidationError(
                    _(
                        "The model name can only contain lowercase characters, digits, underscores and dots."
                    )
                )

    @api.constrains("order", "field_id")
    def _check_order(self) -> None:
        for model in self:
            try:
                model._check_qorder(model.order)
            except UserError as e:
                _debug.logic(
                    "constraint.rejected", model=model.model, reason="invalid_order"
                )
                raise ValidationError(str(e)) from None
            stored_fields = set(
                model.field_id.filtered("store").mapped("name") + models.MAGIC_COLUMNS
            )
            if model.model in self.env:
                stored_fields.update(
                    fname
                    for fname, fval in self.env[model.model]._fields.items()
                    if fval.inherited and fval.base_field.store
                )

            for order_part in model.order.split(","):
                order_match = models.regex_order.match(order_part)
                field = order_match["field"] if order_match else None
                if field and field not in stored_fields:
                    _debug.logic(
                        "constraint.rejected",
                        model=model.model,
                        field=field,
                        reason="order_field_not_stored",
                    )
                    raise ValidationError(
                        _(
                            "Unable to order by %s: fields used for ordering must be present on the model and stored.",
                            field,
                        )
                    )

    @api.constrains("fold_name")
    def _check_fold_name(self) -> None:
        for model in self:
            if model.fold_name and model.fold_name not in model.field_id.mapped("name"):
                _debug.logic(
                    "constraint.rejected",
                    model=model.model,
                    fold_name=model.fold_name,
                    reason="fold_field_unknown",
                )
                raise ValidationError(
                    _("The value of 'Fold Field' should be a field name of the model.")
                )

    _model_uniq = models.Constraint(
        "UNIQUE (model)", "Each model must have a unique name."
    )

    def _get(self, name: str) -> Self:
        model_id = self._get_id(name) if name else False
        return self.sudo().browse(model_id)

    @tools.ormcache("name", cache="stable")
    def _get_id(self, name: str) -> int | None:
        model_id = self.sudo().search([("model", "=", name)], limit=1).id or None
        _debug.perf.count("model_id.cache_miss", model=name, found=bool(model_id))
        return model_id

    def _drop_table(self) -> None:
        for model in self:
            if (current_model := self.env.get(model.model)) is not None:
                if current_model._abstract:
                    _debug.logic(
                        "drop_table.skipped", model=model.model, reason="abstract"
                    )
                    continue

                table = current_model._table
                kind = sql.get_table_kind(self.env.cr, table)
                _debug.lifecycle(
                    "drop_table", model=model.model, table=table, kind=kind
                )
                if kind == sql.TableKind.View:
                    self.env.cr.execute(SQL("DROP VIEW %s", SQL.identifier(table)))
                elif kind == sql.TableKind.Regular:
                    self.env.cr.execute(
                        SQL("DROP TABLE %s CASCADE", SQL.identifier(table))
                    )
                elif kind is not None:
                    _debug.logic(
                        "drop_table.skipped",
                        model=model.model,
                        table=table,
                        reason="unmanaged_kind",
                    )
                    _logger.warning(
                        "Unable to drop table %r of model %r: unmanaged or unknown table type %r",
                        table,
                        model.model,
                        kind,
                    )
            else:
                _debug.logic(
                    "drop_table.skipped", model=model.model, reason="not_in_registry"
                )
                _logger.warning(
                    "The model %s could not be dropped because it did not exist in the registry.",
                    model.model,
                )

    def _unlink_except_module_data(self) -> None:
        for model in self:
            if model.state != "manual":
                _debug.logic("unlink.rejected", model=model.model, reason="base_model")
                raise UserError(
                    _(
                        "Model “%s” contains module data and cannot be removed.",
                        model.name,
                    )
                )

    @override
    def unlink(self) -> bool:
        if not self.env.context.get(MODULE_UNINSTALL_FLAG):
            self._unlink_except_module_data()
        manual_models = self.filtered(lambda model: model.state == "manual")
        _debug.lifecycle(
            "unlink",
            models=self.mapped("model"),
            manual=len(manual_models),
            uninstall=bool(self.env.context.get(MODULE_UNINSTALL_FLAG)),
        )
        manual_models.field_id.filtered(lambda f: f.state == "manual")._prepare_update()
        (self - manual_models).field_id._prepare_update()

        relational_fields = self.env["ir.model.fields"].search(
            [("relation", "in", self.mapped("model"))]
        )
        _debug.pipeline("unlink.relational_fields", count=len(relational_fields))
        relational_fields.unlink()

        crons = (
            self.env["ir.cron"]
            .with_context(active_test=False)
            .search([("model_id", "in", self.ids)])
        )
        crons.unlink()
        model_data = self.env["ir.model.data"].search(
            [("model", "in", self.mapped("model"))]
        )
        model_data.unlink()
        _debug.pipeline("unlink_cascade", crons=len(crons), xmlids=len(model_data))

        # while the tables their referrers live in still exist
        self._unlink_inheritance_rows_cascaded()

        self.field_id._drop_m2m_tables()
        self._drop_table()
        res = super().unlink()

        if not self.env.context.get(MODULE_UNINSTALL_FLAG):
            self.env.flush_all()
            with _debug.perf("registry_setup_after_unlink", cr=self.env.cr):
                self.pool.setup_models(self.env.cr, [])

        return res

    @override
    def write(self, vals: dict[str, Any]) -> bool:
        for unmodifiable_field in ("model", "state", "abstract", "transient"):
            if unmodifiable_field in vals and any(
                rec[unmodifiable_field] != vals[unmodifiable_field] for rec in self
            ):
                _debug.logic(
                    "write.rejected",
                    models=self.mapped("model"),
                    field=unmodifiable_field,
                    reason="unmodifiable",
                )
                raise UserError(
                    _(
                        "Field %s cannot be modified on models.",
                        self._fields[unmodifiable_field]._description_string(self.env),
                    )
                )
        if "field_id" in vals:
            commands = [op for op in vals["field_id"] if op[0] != 4]
            if len(commands) != len(vals["field_id"]):
                _debug.logic(
                    "write.field_links_dropped",
                    dropped=len(vals["field_id"]) - len(commands),
                )
            vals = dict(vals, field_id=commands)
        if _debug.lifecycle.enabled:
            _debug.lifecycle("write", models=self.mapped("model"), fields=list(vals))
        before = self._manual_class_source()
        res = super().write(vals)
        if before != self._manual_class_source():
            self.env.flush_all()
            with _debug.perf("registry_setup_after_write", cr=self.env.cr):
                self.pool.setup_models(self.env.cr, [])
        return res

    def _manual_class_source(self) -> list[tuple[Any, ...]]:
        manual = self.filtered(lambda rec: rec.state == "manual")
        if not manual:
            return []
        manual = manual.with_context(lang="en_US")
        return [
            tuple(rec[fname] for fname in MANUAL_CLASS_MUTABLE_FIELDS) for rec in manual
        ]

    @api.model_create_multi
    @override
    def create(self, vals_list: list[ValuesType]) -> Self:
        res = super().create(vals_list)
        manual_models = [rec.model for rec in res if rec.state == "manual"]
        _debug.lifecycle("create", count=len(res), manual=manual_models)
        if manual_models:
            with _debug.perf("reload_schema", cr=self.env.cr, models=manual_models):
                reload_schema(self.env, [], manual_models)
        return res

    @api.model
    @override
    def name_create(self, name: str) -> tuple[int, str]:
        slug = re.sub(r"[^a-z0-9]+", "_", remove_accents(name).lower()).strip("_")
        ir_model = self.create(
            {
                "name": name,
                "model": f"x_{slug}" if slug else "x_",
            }
        )
        _debug.lifecycle("name_create", model=ir_model.model, slug=bool(slug))
        return ir_model.id, ir_model.display_name

    def _prepare_model_vals(self, model: models.BaseModel) -> dict[str, Any]:
        return {
            "model": model._name,
            "name": model._description,
            "order": model._order or "id",
            "info": next(
                (
                    cls.__doc__
                    for cls in self.env.registry[model._name].mro()
                    if cls.__doc__ and getattr(cls, "_name", None) == model._name
                ),
                None,
            ),
            "state": "manual" if model._custom else "base",
            "abstract": model._abstract,
            "transient": model._transient,
            "fold_name": model._fold_name,
        }

    @api.model
    def _prewarm_ids(self, model_names: list[str]) -> list[int]:
        if not model_names:
            return []
        cache = self._get_id.__cache__
        generation = cache.get_cache_generation(self)
        model_ids = []
        for name, id_ in self.env.execute_query(
            SQL("SELECT model, id FROM ir_model WHERE model = ANY(%s)", model_names)
        ):
            cache.add_value(self, name, cache_value=id_, generation=generation)
            model_ids.append(id_)
        _debug.perf.count(
            "prewarm_ids", requested=len(model_names), found=len(model_ids)
        )
        return model_ids

    @api.model
    def _prewarm_names(self, model_names: list[str]) -> None:
        model_ids = self._prewarm_ids(model_names)
        with _debug.perf("prewarm_names", cr=self.env.cr, models=len(model_ids)):
            self.sudo().browse(model_ids).fetch(["name"])

    def _reflect_models(self, model_names: list[str]) -> None:
        if not model_names:
            _debug.logic("reflect_models.skipped", reason="no_models")
            return
        id_cache_generation = self._get_id.__cache__.get_cache_generation(self)
        vals_list = [
            self._prepare_model_vals(self.env[model_name]) for model_name in model_names
        ]
        cols = list(vals_list[0])
        expected = [tuple(vals[col] for col in cols) for vals in vals_list]

        model_ids: dict[str, int] = {}
        existing: dict[str, tuple[Any, ...]] = {}
        for row in select_en(self, ["id"] + cols, model_names):
            model_ids[row[1]] = row[0]
            existing[row[1]] = row[1:]

        rows = [row for row in expected if existing.get(row[0]) != row]
        _debug.pipeline(
            "reflect_models",
            models=len(model_names),
            existing=len(existing),
            changed=[row[0] for row in rows],
        )
        if rows:
            with _debug.perf("reflect_models.upsert", cr=self.env.cr, rows=len(rows)):
                ids = upsert_en(self, cols, rows, ["model"])
            for row, id_ in zip(rows, ids, strict=True):
                model_ids[row[0]] = id_
            self.pool.post_init(mark_modified, self.browse(ids), cols[1:])

        add_value = self._get_id.__cache__.add_value
        for name, id_ in model_ids.items():
            add_value(self, name, cache_value=id_, generation=id_cache_generation)

        module = self.env.context.get("module")
        if not module:
            _debug.logic("reflect_models.no_xmlids", reason="no_module_in_context")
            return

        data_list = []
        for model_name, model_id in model_ids.items():
            model = self.env[model_name]
            if model._module == module:
                xml_id = model_xmlid(module, model_name)
                record = self.browse(model_id)
                data_list.append({"xml_id": xml_id, "record": record})
        _debug.pipeline("reflect_models_xmlids", module=module, xmlids=len(data_list))
        self.env["ir.model.data"]._update_xmlids(data_list)

    @api.model
    def _get_manual_model_data(self) -> list[dict[str, Any]]:
        self.env.cr.execute(
            "SELECT * FROM ir_model WHERE state = 'manual'", prepare=False
        )
        manual_models = self.env.cr.dictfetchall()
        for model_data in manual_models:
            model_data["name"] = (model_data["name"] or {}).get("en_US")
        _debug.perf.count("manual_model_data.loaded", count=len(manual_models))
        return manual_models

    @api.model
    def _prepare_class_attrs(self, model_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "_name": model_data["model"],
            "_description": model_data["name"],
            "_module": False,
            "_custom": True,
            "_abstract": bool(model_data["abstract"]),
            "_transient": bool(model_data["transient"]),
            "_order": model_data["order"],
            "_fold_name": model_data["fold_name"],
            "__doc__": model_data["info"],
        }

    @api.model
    def _is_manual_name(self, name: str) -> bool:
        return models.is_manual_name(name)

    @api.model
    def _check_manual_name(self, name: str) -> None:
        if not self._is_manual_name(name):
            _debug.logic("constraint.rejected", model=name, reason="not_manual_name")
            raise ValidationError(_("The model name must start with 'x_'."))


class IrModelInherit(models.Model):
    _name = "ir.model.inherit"
    _description = "Model Inheritance Tree"
    _log_access = False

    model_id = fields.Many2one(
        comodel_name="ir.model",
        required=True,
        ondelete="cascade",
    )
    parent_id = fields.Many2one(
        comodel_name="ir.model",
        required=True,
        ondelete="cascade",
    )
    parent_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        ondelete="cascade",
    )

    _uniq = models.Constraint(
        "UNIQUE(model_id, parent_id)", "Models inherits from another only once"
    )

    def _reflect_inherits(self, model_names: list[str]) -> None:
        module_mapping = self._prepare_inherit_mapping(model_names)
        _debug.pipeline(
            "reflect_inherits", models=len(model_names), links=len(module_mapping)
        )
        if not module_mapping:
            return

        inh_ids = self._upsert_inherit_rows(model_names, module_mapping)

        involved = self.env["ir.model"].browse(
            id_ for item in module_mapping for id_ in item[:2]
        )
        involved.fetch(["model"])
        xml_name = {rec.id: rec.model for rec in involved}
        data_list = []
        for (
            model_id,
            parent_id,
            parent_field_id,
        ), modules in module_mapping.items():
            record_id = inh_ids[(model_id, parent_id, parent_field_id)]
            data_list += [
                {
                    "xml_id": inherit_xmlid(
                        module, xml_name[model_id], xml_name[parent_id]
                    ),
                    "record": self.browse(record_id),
                }
                for module in modules
            ]

        _debug.pipeline("reflect_inherits.xmlids", xmlids=len(data_list))
        self.env["ir.model.data"]._update_xmlids(data_list)

    def _prepare_inherit_mapping(
        self, model_names: list[str]
    ) -> dict[tuple[int, int, int | None], OrderedSet]:
        IrModel = self.env["ir.model"]
        definitions: dict[str, list[type[models.BaseModel]]] = {
            model_name: [
                cls
                for cls in reversed(type(self.env[model_name]).mro())
                if models.is_model_definition(cls)
            ]
            for model_name in model_names
        }
        IrModel._prewarm_ids(
            list(
                unique(
                    name
                    for model_name, classes in definitions.items()
                    for cls in classes
                    for name in (model_name, *cls._inherit, *cls._inherits)
                )
            )
        )
        get_model_id = IrModel._get_id

        module_mapping: defaultdict[tuple[int, int, int | None], OrderedSet] = (
            defaultdict(OrderedSet)
        )
        for model_name, classes in definitions.items():
            model_id = get_model_id(model_name)
            if model_id is None:
                _logger.debug(
                    "Inheritance of %r not reflected: no ir_model row yet",
                    model_name,
                )
                _debug.logic("inherit_skipped_no_model_row", model=model_name)
                continue
            get_field_id = (
                self.env["ir.model.fields"]._get_ids_by_name(model_name).get
                if any(cls._inherits for cls in classes)
                else {}.get
            )
            for cls in classes:
                items = self._get_inherit_items(
                    cls, model_name, model_id, get_model_id, get_field_id
                )
                for item in items:
                    module_mapping[item].add(cls._module)
        return module_mapping

    @staticmethod
    def _get_inherit_items(
        definition: type[models.BaseModel],
        model_name: str,
        model_id: int,
        get_model_id: Callable[[str], int | None],
        get_field_id: Callable[[str], int | None],
    ) -> list[tuple[int, int, int | None]]:
        inherit_parents = [
            parent_name
            for parent_name in definition._inherit
            if parent_name not in ("base", model_name)
        ]
        parent_ids = {}
        for parent_name in (*inherit_parents, *definition._inherits):
            parent_id = get_model_id(parent_name)
            if parent_id is None:
                _logger.debug(
                    "Inheritance of %r from %r not reflected: no ir_model row yet",
                    model_name,
                    parent_name,
                )
                _debug.logic(
                    "inherit_skipped_no_parent_row",
                    model=model_name,
                    parent=parent_name,
                )
                continue
            parent_ids[parent_name] = parent_id

        inherit_parents = [name for name in inherit_parents if name in parent_ids]
        delegated = [name for name in definition._inherits if name in parent_ids]

        if overlap := set(inherit_parents) & set(delegated):
            _debug.logic(
                "inherit.rejected",
                model=model_name,
                overlap=sorted(overlap),
                reason="inherit_and_delegate",
            )
            raise ValueError(
                f"Model {model_name!r} both inherits from and delegates "
                f"to {sorted(overlap)}: ir_model_inherit is unique on "
                "(model_id, parent_id) and cannot record both links."
            )

        items: list[tuple[int, int, int | None]] = [
            (model_id, parent_ids[parent_name], None) for parent_name in inherit_parents
        ]
        items.extend(
            (
                model_id,
                parent_ids[parent_name],
                get_field_id(definition._inherits[parent_name]),
            )
            for parent_name in delegated
        )
        return items

    def _upsert_inherit_rows(
        self,
        model_names: list[str],
        module_mapping: dict[tuple[int, int, int | None], OrderedSet],
    ) -> dict[tuple[int, int, int | None], int]:
        cr = self.env.cr
        cr.execute(
            """
                SELECT i.id, i.model_id, i.parent_id, i.parent_field_id
                  FROM ir_model_inherit i
                  JOIN ir_model m
                    ON m.id = i.model_id
                 WHERE m.model = ANY(%s)
            """,
            [list(model_names)],
        )
        existing = {}
        inh_ids = {}
        for iid, model_id, parent_id, parent_field_id in cr.fetchall():
            inh_ids[(model_id, parent_id, parent_field_id)] = iid
            existing[(model_id, parent_id)] = parent_field_id

        sentinel = object()
        cols = ["model_id", "parent_id", "parent_field_id"]
        rows = [
            item
            for item in module_mapping
            if existing.get(item[:2], sentinel) != item[2]
        ]
        _debug.perf.count(
            "upsert_inherit_rows", existing=len(existing), changed=len(rows)
        )
        if rows:
            ids = upsert_en(self, cols, rows, ["model_id", "parent_id"])
            inh_ids.update(dict(zip(rows, ids, strict=True)))
            self.pool.post_init(mark_modified, self.browse(ids), cols[1:])
        return inh_ids
