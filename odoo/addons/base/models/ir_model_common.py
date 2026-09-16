from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from itertools import batched
from typing import TYPE_CHECKING, Any

from psycopg.types.json import Jsonb

from odoo import api, models
from odoo.api import MODULE_UNINSTALL_FLAG  # noqa: F401 - re-exported downstream
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL
from odoo.tools.safe_eval import datetime, dateutil, safe_eval, time
from odoo.tools.translate import LazyTranslate

if TYPE_CHECKING:
    from odoo.db.cursor import BaseCursor

_lt = LazyTranslate(__name__)
_debug = DebugLog(__name__)

ACCESS_MODES = ("read", "write", "create", "unlink")


def check_access_mode(mode: str) -> None:
    if mode not in ACCESS_MODES:
        _debug.logic("access_mode.rejected", mode=mode)
        raise ValueError(
            f"Invalid access mode {mode!r}: expected one of {ACCESS_MODES}."
        )


def access_mode_columns(alias: str) -> dict[str, SQL]:
    return {mode: SQL.identifier(alias, f"perm_{mode}") for mode in ACCESS_MODES}


def unloaded_module_scope(env: Any) -> tuple[int, str | None] | None:
    registry = env.registry
    if registry.ready:
        return None
    return len(registry.loaded_modules), env.context.get("install_module")


def unloaded_module_clause(env: Any, model: str, alias: str) -> SQL:
    registry = env.registry
    loaded_modules = list(registry.loaded_modules)
    if registry.ready or not loaded_modules:
        _debug.logic(
            "unloaded_module_clause.skipped",
            model=model,
            reason="ready" if registry.ready else "no_modules",
        )
        return SQL("")
    if install_module := env.context.get("install_module"):
        loaded_modules.append(install_module)
    _debug.logic(
        "unloaded_module_clause.applied", model=model, modules=len(loaded_modules)
    )
    return SQL(
        """AND NOT EXISTS (
                SELECT 1 FROM ir_model_data d
                WHERE d.model = %s AND d.res_id = %s.id
                  AND d.module <> ALL(%s)
            )""",
        model,
        SQL.identifier(alias),
        loaded_modules,
    )


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

SAFE_EVAL_BASE = {
    "datetime": datetime,
    "dateutil": dateutil,
    "time": time,
}


def prepare_compute(
    text: str, deps: str | None, origin: str = "unknown"
) -> Callable[[models.BaseModel], Any]:
    filename = f"<compute {origin}>"

    def compute(self: models.BaseModel) -> None:
        with _debug.perf("manual_compute", cr=self.env.cr, origin=origin, records=self):
            safe_eval(
                text, SAFE_EVAL_BASE | {"self": self}, mode="exec", filename=filename
            )

    dep_names = [name.strip() for name in deps.split(",")] if deps else []
    dep_names = [name for name in dep_names if name]
    _debug.lifecycle("compute_prepared", origin=origin, depends=len(dep_names))
    return api.depends(*dep_names)(compute)


def mark_modified(records: models.BaseModel, fnames: list[str]) -> None:
    field_objs = [records._fields[fname] for fname in fnames]
    _debug.lifecycle(
        "mark_modified", model=records._name, records=len(records), fields=fnames
    )
    with records.env.protecting(field_objs, records):
        records.modified(fnames)


def compute_modules(records: models.BaseModel) -> None:
    installed = records.env["ir.module.module"].search_fetch(
        [("state", "=", "installed")], ["name"]
    )
    installed_names = set(installed.mapped("name"))
    xml_ids = records._get_external_ids()
    _debug.perf.count(
        "compute_modules",
        model=records._name,
        records=len(records),
        installed=len(installed_names),
    )
    for record in records:
        module_names = {xml_id.split(".")[0] for xml_id in xml_ids[record.id]}
        record.modules = ", ".join(sorted(installed_names & module_names))


def reload_schema(
    env: api.Environment,
    setup_models: Collection[str],
    init_models: Collection[str] = (),
) -> None:
    env.flush_all()
    registry = env.registry
    with _debug.perf("reload_schema_setup", cr=env.cr, models=len(setup_models)):
        registry.setup_models(env.cr, setup_models)
    if init_models:
        affected_models = registry.get_descendants(init_models, "_inherits")
        with _debug.perf(
            "reload_schema_init",
            cr=env.cr,
            models=len(init_models),
            affected=len(affected_models),
        ):
            registry.init_models(
                env.cr, affected_models, dict(env.context, update_custom_fields=True)
            )


def _model_slug(model_name: str) -> str:
    return model_name.replace(".", "_")


def model_xmlid(module: str, model_name: str) -> str:
    return f"{module}.model_{_model_slug(model_name)}"


def inherit_xmlid(module: str, model_name: str, parent_name: str) -> str:
    return (
        f"{module}.model_inherit__{_model_slug(model_name)}__{_model_slug(parent_name)}"
    )


def field_xmlid(module: str, model_name: str, field_name: str) -> str:
    return f"{module}.field_{_model_slug(model_name)}__{field_name}"


def selection_xmlid(module: str, model_name: str, field_name: str, value: str) -> str:
    xvalue = value.replace(".", "_").replace(" ", "_").lower()
    return f"{module}.selection__{_model_slug(model_name)}__{field_name}__{xvalue}"


def query_insert(
    cr: BaseCursor, table: str, rows: list[dict[str, Any]] | Mapping[str, Any]
) -> list[int]:
    if isinstance(rows, Mapping):
        rows = [rows]
    if not rows:
        return []
    cols = list(rows[0])
    _debug.perf.count("query_insert", table=table, rows=len(rows), columns=len(cols))
    return cr.copy_from(
        table,
        cols,
        [tuple(row[col] for col in cols) for row in rows],
        returning_ids=True,
    )


def query_update(
    cr: BaseCursor, table: str, values: dict[str, Any], selectors: list[str]
) -> list[int]:
    selector_set = set(selectors)
    assignments = [
        SQL("%s = %s", SQL.identifier(key), val)
        for key, val in values.items()
        if key not in selector_set
    ]
    if not assignments:
        _debug.logic("query_update.rejected", table=table, reason="no_assignments")
        raise ValueError(
            f"query_update: no columns to update on {table!r}; every key in "
            f"{list(values)} is a selector ({selectors}), so the SET clause "
            "would be empty."
        )
    query = SQL(
        "UPDATE %s SET %s WHERE %s RETURNING id",
        SQL.identifier(table),
        SQL(", ").join(assignments),
        SQL(" AND ").join(
            SQL("%s = %s", SQL.identifier(key), values[key]) for key in selectors
        ),
    )
    cr.execute(query)
    ids = [row[0] for row in cr.fetchall()]
    _debug.perf.count("query_update", table=table, rows=len(ids))
    return ids


def select_en(
    model: models.BaseModel, fnames: list[str], model_names: list[str]
) -> list[tuple[Any, ...]]:
    if not model_names:
        _debug.logic("select_en.skipped", model=model._name, reason="no_models")
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
    rows = model.env.execute_query(query)
    _debug.perf.count(
        "select_en", model=model._name, models=len(model_names), rows=len(rows)
    )
    return rows


def _prepare_upsert_query(
    model: models.BaseModel,
    fnames: list[str],
    conflict: list[str],
    values: SQL,
) -> SQL:
    fields = model._fields
    comma = SQL(", ").join
    col_ids = [SQL.identifier(fname) for fname in fnames]

    def _pg_cast(fname: str) -> SQL:
        ct = fields[fname].column_type
        if ct and ct[0] not in ("varchar", "text"):
            return SQL("::%s", SQL.identifier(ct[0]))
        return SQL("")

    casts = [_pg_cast(fname) for fname in fnames]
    s_cols = [
        SQL("s.%s%s", col_id, cast) for col_id, cast in zip(col_ids, casts, strict=True)
    ]
    on_pred = SQL(" AND ").join(
        SQL("t.%s = s.%s%s", SQL.identifier(c), SQL.identifier(c), _pg_cast(c))
        for c in conflict
    )
    assignments = comma(
        (
            SQL(
                """%s = CASE
                    WHEN t.%s ->> 'en_US' IS DISTINCT FROM s.%s%s ->> 'en_US'
                        THEN s.%s%s
                    ELSE COALESCE(t.%s, '{}'::jsonb) || s.%s%s
                   END""",
                col_id,
                col_id,
                col_id,
                cast,
                col_id,
                cast,
                col_id,
                col_id,
                cast,
            )
            if fields[fname].translate is True
            else SQL("%s = s.%s%s", col_id, col_id, cast)
        )
        for fname, col_id, cast in zip(fnames, col_ids, casts, strict=True)
    )
    returning = comma(
        [SQL("NEW.id")] + [SQL("NEW.%s", SQL.identifier(c)) for c in conflict]
    )
    return SQL(
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
        values=values,
        cols=comma(col_ids),
        on_pred=on_pred,
        assignments=assignments,
        s_cols=comma(s_cols),
        returning=returning,
    )


def upsert_en(
    model: models.BaseModel,
    fnames: list[str],
    rows: list[tuple[Any, ...]],
    conflict: list[str],
) -> list[int]:
    if not rows:
        _debug.logic("upsert_en.skipped", model=model._name, reason="no_rows")
        return []
    if not fnames:
        _debug.logic("upsert_en.rejected", model=model._name, reason="no_fnames")
        raise ValueError("upsert_en: fnames must not be empty")

    fields = model._fields

    if bad := [c for c in conflict if fields[c].translate]:
        _debug.logic(
            "upsert_en.rejected",
            model=model._name,
            reason="translated_conflict",
            columns=len(bad),
        )
        raise ValueError(
            f"upsert_en: conflict columns cannot be translated fields (got {bad}); "
            "the RETURNING/reorder logic assumes scalar, hashable keys."
        )

    conflict_indices = [fnames.index(c) for c in conflict]
    keys = [tuple(row[i] for i in conflict_indices) for row in rows]
    if len(set(keys)) != len(keys):
        _debug.logic(
            "upsert_en.rejected",
            model=model._name,
            reason="duplicate_keys",
            rows=len(keys),
            distinct=len(set(keys)),
        )
        raise ValueError(
            f"upsert_en: rows are not unique on conflict columns {conflict}; "
            "MERGE cannot resolve duplicate source keys."
        )

    def identity(val: Any) -> Any:
        return val

    def jsonify(val: Any) -> Any:
        return Jsonb({"en_US": val}) if val is not None else val

    wrappers = [(jsonify if fields[fname].translate else identity) for fname in fnames]
    values = [
        tuple(func(val) for func, val in zip(wrappers, row, strict=True))
        for row in rows
    ]

    comma = SQL(", ").join
    batch_size = 65000 // len(fnames) or 1
    key_to_id = {}
    with _debug.perf(
        "upsert_en",
        cr=model.env.cr,
        model=model._name,
        rows=len(rows),
        columns=len(fnames),
        batch_size=batch_size,
    ):
        for batch in batched(values, batch_size, strict=False):
            query = _prepare_upsert_query(model, fnames, conflict, comma(batch))
            for result_row in model.env.execute_query(query):
                key_to_id[result_row[1:]] = result_row[0]

    return [key_to_id[key] for key in keys]
