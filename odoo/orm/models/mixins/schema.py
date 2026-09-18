import logging

import psycopg
import psycopg.errors

from odoo.db import schema as sql
from odoo.db.errors import failed_statement_verb
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, format_list, ormcache

from ... import decorators as api
from ...domain import Domain
from ...validation import check_object_name
from ._model_stubs import _ModelStubs

_logger = logging.getLogger("odoo.models")
_debug = DebugLog(__name__)


class SchemaMixin(_ModelStubs):
    __slots__ = ()

    def _update_parent_path_of_table(self) -> None:
        if not self._parent_store:
            return

        _logger.info("Computing parent_path for table %s...", self._table)
        query = SQL(
            """ WITH RECURSIVE __parent_store_compute(id, parent_path) AS (
                    SELECT row.id, concat(row.id, '/')
                    FROM %(table)s row
                    WHERE row.%(parent)s IS NULL
                UNION
                    SELECT row.id, concat(comp.parent_path, row.id, '/')
                    FROM %(table)s row, __parent_store_compute comp
                    WHERE row.%(parent)s = comp.id
                )
                UPDATE %(table)s row SET parent_path = comp.parent_path
                FROM __parent_store_compute comp
                WHERE row.id = comp.id """,
            table=SQL.identifier(self._table),
            parent=SQL.identifier(self._parent_name),
        )
        self.env.cr.execute(query)
        _debug.perf.count(
            "schema.parent_path_computed",
            model=self._name,
            rows=self.env.cr.rowcount,
        )
        self.invalidate_model(["parent_path"])

    def _check_removed_columns(self) -> None:
        if self._abstract:
            return
        cr = self.env.cr
        cols = {name for name, field in self._fields.items() if field.is_column}
        stale = 0  # debuglog
        for col_name, col_data in sql.get_table_columns(cr, self._table).items():
            if col_name in cols:
                continue
            stale += 1  # debuglog
            _logger.debug(
                "column %s is in the table %s but not in the corresponding object %s",
                col_name,
                self._table,
                self._name,
            )
            if col_data["is_nullable"] == "NO":
                _debug.logic(
                    "schema.removed_column_not_null_dropped",
                    model=self._name,
                    column=col_name,
                )
                sql.drop_not_null(cr, self._table, col_name)
        if _debug.perf.enabled and stale:
            _debug.perf.count(
                "schema.removed_columns_found",
                model=self._name,
                table=self._table,
                stale=stale,
                declared=len(cols),
            )

    def _init_column(self, column_name: str, *, new_column: bool = False) -> None:
        field = self._fields[column_name]
        if field.default:
            value = field.default(self)
            value = field.convert_to_write(value, self)
            value = field.convert_to_column_insert(value, self)
        else:
            value = None
        necessary = (
            (value is not None) if not field.is_boolean or field.required else value
        )
        if necessary:
            _logger.debug(
                "Table '%s': setting default value of new column %s to %r",
                self._table,
                column_name,
                value,
            )
            self.env.cr.execute(
                SQL(
                    "UPDATE %(table)s SET %(field)s = %(value)s",
                    table=SQL.identifier(self._table),
                    field=SQL.identifier(column_name),
                    value=value,
                )
                if new_column
                else SQL(
                    "UPDATE %(table)s SET %(field)s = %(value)s WHERE %(field)s IS NULL",
                    table=SQL.identifier(self._table),
                    field=SQL.identifier(column_name),
                    value=value,
                )
            )
            _debug.lifecycle(
                "schema.column_default_set",
                model=getattr(self, "_name", None),
                table=self._table,
                column=column_name,
                new_column=new_column,
                rows=getattr(self.env.cr, "rowcount", None),
            )

    @ormcache()
    def _has_rows_in_table(self) -> bool:
        has_rows = self.env.backend.has_rows_beyond(self, 0)
        _debug.perf.count(
            "schema.rows_probed",
            model=self._name,
            table=self._table,
            rows=has_rows,
        )
        return has_rows

    def _auto_init(self) -> None:
        check_object_name(self._name)

        self = self.with_context(prefetch_fields=False)

        cr = self.env.cr
        update_custom_fields = self.env.context.get("update_custom_fields", False)
        must_create_table = not sql.table_exists(cr, self._table)
        parent_path_compute = False
        _debug.pipeline(
            "schema.auto_init",
            model=self._name,
            table=self._table,
            auto=self._auto,
            create_table=must_create_table,
            update_custom_fields=update_custom_fields,
        )

        if self._auto:
            if must_create_table:

                def get_column_type(field):
                    return field.column_type[1] + (
                        " NOT NULL" if field.required else ""
                    )

                root_table = self._table_inheritance_root
                inherits = (
                    root_table if root_table and root_table != self._table else None
                )
                if inherits and not sql.table_exists(cr, inherits):
                    sql.create_model_table(cr, inherits)
                    _debug.lifecycle(
                        "schema.root_table_created", model=self._name, table=inherits
                    )
                sql.create_model_table(
                    cr,
                    self._table,
                    self._description,
                    [
                        (field.name, get_column_type(field), field.string)
                        for field in sorted(
                            self._fields.values(), key=lambda f: f.column_order
                        )
                        if field.name != "id" and field.is_column
                    ],
                    inherits=inherits,
                )
                _debug.lifecycle(
                    "schema.table_created", model=self._name, table=self._table
                )

            if self._parent_store:
                if not sql.column_exists(cr, self._table, "parent_path"):
                    sql.create_column(
                        self.env.cr, self._table, "parent_path", "VARCHAR"
                    )
                    parent_path_compute = True
                    _debug.lifecycle(
                        "schema.parent_path_column_added",
                        model=self._name,
                        table=self._table,
                    )
                self._check_parent_path()

            columns = sql.get_table_columns(cr, self._table)
            fields_to_compute = []
            new_columns = 0  # debuglog

            for field in sorted(self._fields.values(), key=lambda f: f.column_order):
                if not field.store:
                    continue
                if field.manual and not update_custom_fields:
                    continue
                new = field.update_db(self, columns)
                if _debug.perf.enabled and new:
                    new_columns += 1  # debuglog
                if new and field.compute:
                    fields_to_compute.append(field)

            _debug.perf.count(
                "schema.columns_updated",
                model=self._name,
                existing=len(columns),
                new=new_columns,
                to_compute=len(fields_to_compute),
            )

            if fields_to_compute:
                self._schedule_new_column_computes(fields_to_compute)

        if self._auto:
            self._add_sql_constraints()

        if parent_path_compute:
            self._update_parent_path_of_table()

    def _schedule_new_column_computes(self, fields_to_compute: list) -> None:
        records = self.browse(
            self.with_context(active_test=False)
            ._search(Domain.TRUE, bypass_access=True)
            .get_result_ids()
        )
        _debug.pipeline(
            "schema.new_column_computes_scheduled",
            model=self._name,
            fields=len(fields_to_compute),
            records=len(records),
        )
        if records:
            for field in fields_to_compute:
                _logger.info("Prepare computation of %s", field)
                self.env.add_to_compute(field, records)

    @api.private
    def init(self) -> None:
        pass

    def _check_parent_path(self) -> None:
        field = self._fields.get("parent_path")
        if field is None:
            raise ValueError(
                f"{self._name} sets _parent_store but declares no parent_path; "
                f"add `parent_path = fields.Char(index=True)` to the model."
            )
        if not field.index:
            raise ValueError(
                f"{self._name}.parent_path must be indexed, because child_of "
                f"resolves through it; add index=True to the field."
            )

    def _add_sql_constraints(self) -> None:
        _debug.pipeline(
            "schema.table_objects",
            model=self._name,
            objects=len(self._table_objects),
        )
        for obj in self._table_objects.values():
            obj.apply_to_database(self)

    @api.model
    def _sql_error_to_message(self, exc: psycopg.Error) -> str:
        if (constraint_name := exc.diag.constraint_name) and (
            cons := self._table_objects.get(constraint_name)
        ):
            if message := self.env.registry.metaschema.constraint_message(
                self.env, self._name, constraint_name
            ):
                _debug.logic(
                    "schema.sql_error.constraint_message",
                    model=self._name,
                    constraint=constraint_name,
                    source="ir.model.constraint",
                )
                return message
            if message := cons.get_error_message(self, exc.diag):
                _debug.logic(
                    "schema.sql_error.constraint_message",
                    model=self._name,
                    constraint=constraint_name,
                    source="table_object",
                )
                return message
        _debug.logic(
            "schema.sql_error.generic",
            model=self._name,
            error=type(exc).__name__,
            constraint=exc.diag.constraint_name,
        )
        return self._sql_error_to_message_generic(exc)

    @api.model
    def _sql_error_to_message_generic(self, exc: psycopg.Error) -> str:
        diag = exc.diag
        unknown = self.env._("Unknown")
        model_string = (
            self.env.registry.metaschema.model_description(self.env, self._name)
            or self._description
        )
        info = {
            "model_display": f"'{model_string}' ({self._name})",
            "table_name": diag.table_name,
            "constraint_name": diag.constraint_name,
        }
        if self._table == diag.table_name:
            columns = sql.get_column_names_in_constraint(
                self.env.cr, diag, check_catalog=True
            )
        else:
            columns = sql.get_column_names_in_constraint(self.env.cr, diag)
            info["model_display"] = unknown
        if not columns:
            info["field_display"] = unknown
        elif len(columns) == 1 and (field := self._fields.get(columns[0])):
            field_string = field._description_string(self.env)
            info["field_display"] = f"'{field_string}' ({field.name})"
        else:
            info["field_display"] = f"'{format_list(self.env, columns)}'"
        _debug.logic(
            "schema.sql_error.classified",
            model=self._name,
            error=type(exc).__name__,
            own_table=self._table == diag.table_name,
            columns=len(columns),
            constraint=diag.constraint_name,
        )

        if isinstance(exc, psycopg.errors.NotNullViolation):
            return self.env._(
                "Missing required value for the field %(field_display)s.\n"
                "Model: %(model_display)s\n"
                "- create/update: a mandatory field is not set\n"
                "- delete: another model requires the record being deleted, you can archive it instead\n",
                **info,
            )

        if isinstance(
            exc,
            (
                psycopg.errors.ForeignKeyViolation,
                psycopg.errors.RestrictViolation,
            ),
        ):
            if len(columns) != 1:
                info["field_display"] = info["constraint_name"]
            if failed_statement_verb(exc) in ("INSERT", "UPDATE", "MERGE", "COPY"):
                return self.env._(
                    "%(field_display)s of %(model_display)s refers to a record "
                    "that does not exist.\n\n"
                    "It may have been deleted meanwhile: reload and pick it again.",
                    **info,
                )
            return self.env._(
                "Another model is using the record you are trying to delete.\n\n"
                "The troublemaker is: %(model_display)s\n"
                "Thanks to the following constraint: %(field_display)s\n"
                "How about archiving the record instead?",
                **info,
            )

        if isinstance(exc, psycopg.errors.UniqueViolation) and columns:
            column_names = [
                self._fields[f].string if f in self._fields else f for f in columns
            ]
            info["field_display"] = (
                f"'{', '.join(columns)}' ({format_list(self.env, column_names)})"
            )
            info["detail"] = diag.message_detail
            return self.env._(
                "The value for %(field_display)s already exists.\n\nDetail: %(detail)s\n",
                **info,
            )

        return str(exc).strip()
