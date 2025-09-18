import logging
import re
from collections import defaultdict
from collections.abc import Mapping
from itertools import batched
from typing import Any, Self

from psycopg.types.json import Jsonb

from odoo import api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import (
    SQL,
    OrderedSet,
    sql,
    unique,
)
from odoo.tools.safe_eval import datetime, dateutil, safe_eval, time
from odoo.tools.translate import LazyTranslate, _
from odoo.orm._typing import ValuesType

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)

# Messages are declared in extenso so they are properly exported in translation terms
ACCESS_ERROR_HEADER = {
    "read": _lt(
        "You are not allowed to access '%(document_kind)s' (%(document_model)s) records."
    ),
    "write": _lt(
        "You are not allowed to modify '%(document_kind)s' (%(document_model)s) records."
    ),
    "create": _lt(
        "You are not allowed to create '%(document_kind)s' (%(document_model)s) records."
    ),
    "unlink": _lt(
        "You are not allowed to delete '%(document_kind)s' (%(document_model)s) records."
    ),
}
ACCESS_ERROR_GROUPS = _lt(
    "This operation is allowed for the following groups:\n%(groups_list)s"
)
ACCESS_ERROR_NOGROUP = _lt("No group currently allows this operation.")
ACCESS_ERROR_RESOLUTION = _lt(
    "Contact your administrator to request access if necessary."
)

MODULE_UNINSTALL_FLAG = "_force_unlink"
RE_ORDER_FIELDS = re.compile(r'"?(\w+)"?\s*(?:asc|desc)?', flags=re.IGNORECASE)

# base environment for doing a safe_eval
SAFE_EVAL_BASE = {
    "datetime": datetime,
    "dateutil": dateutil,
    "time": time,
}


def make_compute(text: str, deps: str | None) -> Any:
    """Return a compute function from its code body and dependencies."""

    def func(self: Any) -> Any:
        return safe_eval(text, SAFE_EVAL_BASE | {"self": self}, mode="exec")

    deps = [arg.strip() for arg in deps.split(",")] if deps else []
    return api.depends(*deps)(func)


def mark_modified(records: Any, fnames: list[str]) -> None:
    """Mark the given fields as modified on records."""
    # protect all modified fields, to avoid them being recomputed
    fields = [records._fields[fname] for fname in fnames]
    with records.env.protecting(fields, records):
        records.modified(fnames)


def model_xmlid(module: str, model_name: str) -> str:
    """Return the XML id of the given model."""
    return f"{module}.model_{model_name.replace('.', '_')}"


def field_xmlid(module: str, model_name: str, field_name: str) -> str:
    """Return the XML id of the given field."""
    return f"{module}.field_{model_name.replace('.', '_')}__{field_name}"


def selection_xmlid(module: str, model_name: str, field_name: str, value: str) -> str:
    """Return the XML id of the given selection."""
    xmodel = model_name.replace(".", "_")
    xvalue = value.replace(".", "_").replace(" ", "_").lower()
    return f"{module}.selection__{xmodel}__{field_name}__{xvalue}"


def query_insert(
    cr: Any, table: str, rows: list[dict[str, Any]] | Mapping[str, Any]
) -> list[int]:
    """Insert rows in a table. ``rows`` is a list of dicts, all with the same
    set of keys. Return the ids of the new rows.
    """
    if isinstance(rows, Mapping):
        rows = [rows]
    if not rows:
        return []
    cols = list(rows[0])
    return cr.copy_from(
        table,
        cols,
        [tuple(row[col] for col in cols) for row in rows],
        returning_ids=True,
    )


def query_update(
    cr: Any, table: str, values: dict[str, Any], selectors: list[str]
) -> list[int]:
    """Update the table with the given values (dict), and use the columns in
    ``selectors`` to select the rows to update.
    """
    query = SQL(
        "UPDATE %s SET %s WHERE %s RETURNING id",
        SQL.identifier(table),
        SQL(",").join(
            SQL("%s = %s", SQL.identifier(key), val)
            for key, val in values.items()
            if key not in selectors
        ),
        SQL(" AND ").join(
            SQL("%s = %s", SQL.identifier(key), values[key]) for key in selectors
        ),
    )
    cr.execute(query)
    return [row[0] for row in cr.fetchall()]


def select_en(
    model: Any, fnames: list[str], model_names: list[str]
) -> list[tuple[Any, ...]]:
    """Select the given columns from the given model's table, with the given WHERE clause.
    Translated fields are returned in 'en_US'.
    """
    if not model_names:
        return []
    cols = SQL(", ").join(
        (
            SQL("%s->>'en_US'", SQL.identifier(fname))
            if model._fields[fname].translate
            else SQL.identifier(fname)
        )
        for fname in fnames
    )
    query = SQL(
        "SELECT %s FROM %s WHERE model = ANY(%s)",
        cols,
        SQL.identifier(model._table),
        list(model_names),
    )
    return model.env.execute_query(query)


def upsert_en(
    model: Any,
    fnames: list[str],
    rows: list[tuple[Any, ...]],
    conflict: list[str],
) -> list[int]:
    """Insert or update the table with the given rows using MERGE.

    :param model: recordset of the model to query
    :param fnames: list of column names
    :param rows: list of tuples, where each tuple value corresponds to a column name
    :param conflict: list of column names for the MERGE ON predicate
    :return: the ids of the inserted or updated rows, in the same order as *rows*
    """

    # for translated fields, we can actually erase the json value, as
    # translations will be reloaded after this
    def identity(val: Any) -> Any:
        return val

    def jsonify(val: Any) -> Any:
        # Jsonb (not Json) so MERGE's USING VALUES source table has jsonb type,
        # matching the target column for the || operator.
        return Jsonb({"en_US": val}) if val is not None else val

    wrappers = [
        (jsonify if model._fields[fname].translate else identity) for fname in fnames
    ]
    values = [
        tuple(func(val) for func, val in zip(wrappers, row, strict=True))
        for row in rows
    ]
    comma = SQL(", ").join
    col_ids = [SQL.identifier(fname) for fname in fnames]

    # Unlike INSERT … VALUES (which resolves NULL types against the target
    # column), MERGE … USING (VALUES …) treats the source as an independent
    # sub-query.  When every value in a column is NULL, PostgreSQL defaults
    # its type to text, causing type mismatches (e.g. text vs jsonb/int4).
    # Add explicit casts on all source-column references to guarantee correct
    # types regardless of NULLs in the batch.
    def _pg_cast(fname: str) -> SQL:
        ct = model._fields[fname].column_type
        if ct and ct[0] not in ("varchar", "text"):
            return SQL("::%s", SQL(ct[0]))
        return SQL("")

    casts = [_pg_cast(fname) for fname in fnames]
    s_cols = [
        SQL("s.%s%s", SQL.identifier(fname), cast)
        for fname, cast in zip(fnames, casts, strict=True)
    ]
    on_pred = SQL(" AND ").join(
        SQL("t.%s = s.%s", SQL.identifier(c), SQL.identifier(c)) for c in conflict
    )
    assignments = comma(
        (
            SQL(
                "%s = COALESCE(t.%s, '{}'::jsonb) || s.%s%s",
                SQL.identifier(fname),
                SQL.identifier(fname),
                SQL.identifier(fname),
                cast,
            )
            if model._fields[fname].translate is True
            else SQL(
                "%s = s.%s%s",
                SQL.identifier(fname),
                SQL.identifier(fname),
                cast,
            )
        )
        for fname, cast in zip(fnames, casts, strict=True)
    )
    # Include conflict columns in RETURNING so we can reconstruct the input
    # order.  Unlike INSERT … ON CONFLICT whose RETURNING preserves VALUES
    # order, MERGE processes rows according to the join strategy, so the
    # RETURNING order is non-deterministic.
    returning = comma(
        [SQL("NEW.id")] + [SQL("NEW.%s", SQL.identifier(c)) for c in conflict]
    )
    # psycopg3 limits query parameters to 65535.  Batch rows so that
    # rows_per_batch * len(fnames) stays well under the limit.
    batch_size = 65000 // len(fnames) or 1
    key_to_id = {}

    for batch in batched(values, batch_size, strict=False):
        query = SQL(
            """
            MERGE INTO %(table)s t
            USING (VALUES %(values)s) AS s(%(cols)s)
            ON %(on_pred)s
            WHEN MATCHED THEN
                UPDATE SET %(assignments)s
            WHEN NOT MATCHED THEN
                INSERT (%(cols)s) VALUES (%(s_cols)s)
            RETURNING %(returning)s
            """,
            table=SQL.identifier(model._table),
            values=comma(batch),
            cols=comma(col_ids),
            on_pred=on_pred,
            assignments=assignments,
            s_cols=comma(s_cols),
            returning=returning,
        )
        # Map conflict-key → id from the (unordered) result set.
        for result_row in model.env.execute_query(query):
            key_to_id[result_row[1:]] = result_row[0]

    conflict_indices = [fnames.index(c) for c in conflict]
    return [key_to_id[tuple(row[i] for i in conflict_indices)] for row in rows]


#
# IMPORTANT: this must be the first model declared in the module
#


class Base(models.AbstractModel):
    """The base model, which is implicitly inherited by all models."""

    _name = "base"
    _description = "Base"


class Unknown(models.AbstractModel):
    """
    Abstract model used as a substitute for relational fields with an unknown
    comodel.
    """

    _name = "_unknown"
    _description = "Unknown"


class IrModel(models.Model):
    _name = "ir.model"
    _description = "Models"
    _order = "model"
    _rec_names_search = ["name", "model"]
    _allow_sudo_commands = False

    def _default_field_id(self) -> list[tuple[int, int, dict[str, Any]]]:
        if self.env.context.get("install_mode"):
            return []  # no default field when importing
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

    name = fields.Char(string="Model Description", translate=True, required=True)
    model = fields.Char(default="x_", required=True)
    order = fields.Char(
        string="Order",
        default="id",
        required=True,
        help='SQL expression for ordering records in the model; e.g. "x_sequence asc, id desc"',
    )
    info = fields.Text(string="Information")
    field_id = fields.One2many(
        "ir.model.fields",
        "model_id",
        string="Fields",
        required=True,
        copy=True,
        default=_default_field_id,
    )
    inherited_model_ids = fields.Many2many(
        "ir.model",
        compute="_inherited_models",
        string="Inherited models",
        help="The list of models that extends the current model.",
    )
    state = fields.Selection(
        [("manual", "Custom Object"), ("base", "Base Object")],
        string="Type",
        default="manual",
        readonly=True,
    )
    access_ids = fields.One2many("ir.model.access", "model_id", string="Access")
    rule_ids = fields.One2many("ir.rule", "model_id", string="Record Rules")
    abstract = fields.Boolean(string="Abstract Model")
    transient = fields.Boolean(string="Transient Model")
    modules = fields.Char(
        compute="_in_modules",
        string="In Apps",
        help="List of modules in which the object is defined or inherited",
    )
    view_ids = fields.One2many("ir.ui.view", compute="_view_ids", string="Views")
    count = fields.Integer(
        compute="_compute_count",
        string="Count (Incl. Archived)",
        help="Total number of records in this model",
    )
    fold_name = fields.Char(
        string="Fold Field",
        help="In a Kanban view where columns are records of this model, the value "
        "of this (boolean) field determines which column should be folded by default.",
    )

    @api.depends()
    def _inherited_models(self) -> None:
        """Batch-resolve inherited models with a single search."""
        self.inherited_model_ids = False
        # Collect all parent model names from the registry (no DB needed)
        all_parent_names = set()
        inherits_by_model: dict[str, list[str]] = {}
        for model in self:
            if (records := self.env.get(model.model)) is not None:
                parent_names = list(records._inherits)
                if parent_names:
                    inherits_by_model[model.model] = parent_names
                    all_parent_names.update(parent_names)
        if not all_parent_names:
            return
        # Single search for all parent model names
        parent_records = {
            rec.model: rec
            for rec in self.search([("model", "in", list(all_parent_names))])
        }
        for model in self:
            if parent_names := inherits_by_model.get(model.model):
                model.inherited_model_ids = self.browse(
                    parent_records[name].id
                    for name in parent_names
                    if name in parent_records
                )

    @api.depends()
    def _in_modules(self) -> None:
        installed_modules = self.env["ir.module.module"].search(
            [("state", "=", "installed")]
        )
        installed_names = set(installed_modules.mapped("name"))
        xml_ids = models.Model._get_external_ids(self)
        for model in self:
            module_names = {xml_id.split(".")[0] for xml_id in xml_ids[model.id]}
            model.modules = ", ".join(sorted(installed_names & module_names))

    @api.depends()
    def _view_ids(self) -> None:
        """Batch-fetch views for all models in a single query."""
        model_names = [m.model for m in self]
        View = self.env["ir.ui.view"]
        views_by_model: dict[str, list[int]] = defaultdict(list)
        if model_names:
            for view in View.search([("model", "in", model_names)]):
                views_by_model[view.model].append(view.id)
        for model in self:
            model.view_ids = View.browse(views_by_model.get(model.model, []))

    @api.depends()
    def _compute_count(self) -> None:
        """Batch-count records using a single UNION ALL query."""
        self.count = 0
        # Collect (table_name, model_name) for concrete models
        table_models: list[tuple[str, str]] = [
            (records._table, model.model)
            for model in self
            if (records := self.env.get(model.model)) is not None
            and not records._abstract
            and records._auto
        ]
        if not table_models:
            return
        # Single UNION ALL: one COUNT(*) per table in one round-trip
        parts = [
            SQL(
                "SELECT %s AS model, COUNT(*) FROM %s",
                model_name,
                SQL.identifier(table),
            )
            for table, model_name in table_models
        ]
        query = SQL(" UNION ALL ").join(parts)
        counts = dict(self.env.execute_query(query))
        for model in self:
            if model.model in counts:
                model.count = counts[model.model]

    @api.constrains("model")
    def _check_model_name(self) -> None:
        for model in self:
            if model.state == "manual":
                self._check_manual_name(model.model)
            if not models.check_object_name(model.model):
                raise ValidationError(
                    _(
                        "The model name can only contain lowercase characters, digits, underscores and dots."
                    )
                )

    @api.constrains("order", "field_id")
    def _check_order(self) -> None:
        for model in self:
            try:
                model._check_qorder(
                    model.order
                )  # regex check for the whole clause ('is it valid sql?')
            except UserError as e:
                raise ValidationError(str(e))
            # add MAGIC_COLUMNS to 'stored_fields' in case 'model' has not been
            # initialized yet, or 'field_id' is not up-to-date in cache
            stored_fields = set(
                model.field_id.filtered("store").mapped("name") + models.MAGIC_COLUMNS
            )
            if model.model in self.env:
                # add fields inherited from models specified via code if they are already loaded
                stored_fields.update(
                    fname
                    for fname, fval in self.env[model.model]._fields.items()
                    if fval.inherited and fval.base_field.store
                )

            order_fields = RE_ORDER_FIELDS.findall(model.order)
            for field in order_fields:
                if field not in stored_fields:
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
                raise ValidationError(
                    _("The value of 'Fold Field' should be a field name of the model.")
                )

    _obj_name_uniq = models.Constraint(
        "UNIQUE (model)", "Each model must have a unique name."
    )

    def _get(self, name: str) -> Self:
        """Return the (sudoed) `ir.model` record with the given name.
        The result may be an empty recordset if the model is not found.
        """
        model_id = self._get_id(name) if name else False
        return self.sudo().browse(model_id)

    @tools.ormcache("name", cache="stable")
    def _get_id(self, name: str) -> int | None:
        self.env.cr.execute("SELECT id FROM ir_model WHERE model=%s", (name,))
        return result[0] if (result := self.env.cr.fetchone()) else None

    def _drop_table(self) -> bool:
        for model in self:
            if (current_model := self.env.get(model.model)) is not None:
                if current_model._abstract:
                    continue

                table = current_model._table
                kind = sql.table_kind(self.env.cr, table)
                if kind == sql.TableKind.View:
                    self.env.cr.execute(SQL("DROP VIEW %s", SQL.identifier(table)))
                elif kind == sql.TableKind.Regular:
                    self.env.cr.execute(
                        SQL("DROP TABLE %s CASCADE", SQL.identifier(table))
                    )
                elif kind is not None:
                    _logger.warning(
                        "Unable to drop table %r of model %r: unmanaged or unknown table type %r",
                        table,
                        model.model,
                        kind,
                    )
            else:
                _logger.warning(
                    "The model %s could not be dropped because it did not exist in the registry.",
                    model.model,
                )
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_if_manual(self) -> None:
        # Prevent manual deletion of module tables
        for model in self:
            if model.state != "manual":
                raise UserError(
                    _(
                        "Model “%s” contains module data and cannot be removed.",
                        model.name,
                    )
                )

    def unlink(self) -> bool:
        # prevent screwing up fields that depend on these models' fields
        manual_models = self.filtered(lambda model: model.state == "manual")
        manual_models.field_id.filtered(lambda f: f.state == "manual")._prepare_update()
        (self - manual_models).field_id._prepare_update()

        # delete fields whose comodel is being removed
        self.env["ir.model.fields"].search(
            [("relation", "in", self.mapped("model"))]
        ).unlink()

        # delete ir_crons created by user
        crons = (
            self.env["ir.cron"]
            .with_context(active_test=False)
            .search([("model_id", "in", self.ids)])
        )
        if crons:
            crons.unlink()

        # delete related ir_model_data
        model_data = self.env["ir.model.data"].search(
            [("model", "in", self.mapped("model"))]
        )
        if model_data:
            model_data.unlink()

        self._drop_table()
        res = super().unlink()

        # Reload registry for normal unlink only. For module uninstall, the
        # reload is done independently in odoo.modules.loading.
        if not self.env.context.get(MODULE_UNINSTALL_FLAG):
            # setup models; this automatically removes model from registry
            self.env.flush_all()
            self.pool._setup_models__(self.env.cr)

        return res

    def write(self, vals: dict[str, Any]) -> bool:
        for unmodifiable_field in ("model", "state", "abstract", "transient"):
            if unmodifiable_field in vals and any(
                rec[unmodifiable_field] != vals[unmodifiable_field] for rec in self
            ):
                raise UserError(
                    _(
                        "Field %s cannot be modified on models.",
                        self._fields[unmodifiable_field]._description_string(self.env),
                    )
                )
        # Filter out operations 4 from field id, because the web client always
        # writes (4,id,False) even for non dirty items.
        if "field_id" in vals:
            vals["field_id"] = [op for op in vals["field_id"] if op[0] != 4]
        res = super().write(vals)
        # ordering has been changed, reload registry to reflect update + signaling
        if "order" in vals or "fold_name" in vals:
            self.env.flush_all()  # _setup_models__ need to fetch the updated values from the db
            # incremental setup will reload custom models
            self.pool._setup_models__(self.env.cr, [])
        return res

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        res = super().create(vals_list)
        manual_models = [
            vals["model"]
            for vals in vals_list
            if vals.get("state", "manual") == "manual"
        ]
        if manual_models:
            # setup models; this automatically adds model in registry
            self.env.flush_all()
            # incremental setup will reload custom models
            self.pool._setup_models__(self.env.cr, [])
            # update database schema
            self.pool.init_models(
                self.env.cr,
                manual_models,
                dict(self.env.context, update_custom_fields=True),
            )
        return res

    @api.model
    def name_create(self, name: str) -> tuple[int, str]:
        """Infer the model from the name. E.g.: 'My New Model' should become 'x_my_new_model'."""
        ir_model = self.create(
            {
                "name": name,
                "model": "x_" + "_".join(name.lower().split(" ")),
            }
        )
        return ir_model.id, ir_model.display_name

    def _reflect_model_params(self, model: Any) -> dict[str, Any]:
        """Return the values to write to the database for the given model."""
        return {
            "model": model._name,
            "name": model._description,
            "order": model._order or "id",
            "info": next(
                (
                    cls.__doc__
                    for cls in self.env.registry[model._name].mro()
                    if cls.__doc__
                ),
                None,
            ),
            "state": "manual" if model._custom else "base",
            "abstract": model._abstract,
            "transient": model._transient,
            "fold_name": model._fold_name,
        }

    def _reflect_models(self, model_names: list[str]) -> None:
        """Reflect the given models."""
        # determine expected and existing rows
        rows = [
            self._reflect_model_params(self.env[model_name])
            for model_name in model_names
        ]
        cols = list(unique(["model"] + list(rows[0])))
        expected = [tuple(row[col] for col in cols) for row in rows]

        model_ids = {}
        existing = {}
        for row in select_en(self, ["id"] + cols, model_names):
            model_ids[row[1]] = row[0]
            existing[row[1]] = row[1:]

        # create or update rows
        rows = [row for row in expected if existing.get(row[0]) != row]
        if rows:
            ids = upsert_en(self, cols, rows, ["model"])
            for row, id_ in zip(rows, ids, strict=True):
                model_ids[row[0]] = id_
            self.pool.post_init(mark_modified, self.browse(ids), cols[1:])

        # update their XML id
        module = self.env.context.get("module")
        if not module:
            return

        data_list = []
        for model_name, model_id in model_ids.items():
            model = self.env[model_name]
            if model._module == module:
                # model._module is the name of the module that last extended model
                xml_id = model_xmlid(module, model_name)
                record = self.browse(model_id)
                data_list.append({"xml_id": xml_id, "record": record})
        self.env["ir.model.data"]._update_xmlids(data_list)

    @api.model
    def _instantiate_attrs(self, model_data: dict[str, Any]) -> dict[str, Any]:
        """Return the attributes to instantiate a custom model definition class
        corresponding to ``model_data``.
        """
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
        return name.startswith("x_")

    @api.model
    def _check_manual_name(self, name: str) -> None:
        if not self._is_manual_name(name):
            raise ValidationError(_("The model name must start with 'x_'."))


class IrModelInherit(models.Model):
    _name = "ir.model.inherit"
    _description = "Model Inheritance Tree"
    _log_access = False

    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade")
    parent_id = fields.Many2one("ir.model", required=True, ondelete="cascade")
    parent_field_id = fields.Many2one(
        "ir.model.fields", ondelete="cascade"
    )  # in case of inherits

    _uniq = models.Constraint(
        "UNIQUE(model_id, parent_id)", "Models inherits from another only once"
    )

    def _reflect_inherits(self, model_names: list[str]) -> None:
        """Reflect the given models' inherits (_inherit and _inherits)."""
        IrModel = self.env["ir.model"]
        get_model_id = IrModel._get_id

        module_mapping = defaultdict(OrderedSet)
        for model_name in model_names:
            get_field_id = self.env["ir.model.fields"]._get_ids(model_name).get
            model_id = get_model_id(model_name)
            model = self.env[model_name]

            for cls in reversed(type(model).mro()):
                if not models.is_model_definition(cls):
                    continue

                items = [
                    (model_id, get_model_id(parent_name), None)
                    for parent_name in cls._inherit
                    if parent_name not in ("base", model_name)
                ] + [
                    (model_id, get_model_id(parent_name), get_field_id(field))
                    for parent_name, field in cls._inherits.items()
                ]

                for item in items:
                    module_mapping[item].add(cls._module)

        if not module_mapping:
            return

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
        if rows:
            ids = upsert_en(self, cols, rows, ["model_id", "parent_id"])
            inh_ids.update(dict(zip(rows, ids, strict=True)))
            self.pool.post_init(mark_modified, self.browse(ids), cols[1:])

        # update their XML id
        IrModel.browse(id_ for item in module_mapping for id_ in item[:2]).fetch(
            ["model"]
        )
        data_list = []
        for (
            model_id,
            parent_id,
            parent_field_id,
        ), modules in module_mapping.items():
            model_name = IrModel.browse(model_id).model.replace(".", "_")
            parent_name = IrModel.browse(parent_id).model.replace(".", "_")
            record_id = inh_ids[(model_id, parent_id, parent_field_id)]
            data_list += [
                {
                    "xml_id": f"{module}.model_inherit__{model_name}__{parent_name}",
                    "record": self.browse(record_id),
                }
                for module in modules
            ]

        self.env["ir.model.data"]._update_xmlids(data_list)


# Re-exports for backward compatibility (classes moved to separate files)
from .ir_model_access import (  # noqa: E402, F401
    IrModelAccess,
    IrModelConstraint,
    IrModelRelation,
)
from .ir_model_data import IrModelData  # noqa: E402, F401
from .ir_model_fields import FIELD_TYPES, IrModelFields  # noqa: E402, F401
from .ir_model_fields_selection import (
    IrModelFieldsSelection,
)
