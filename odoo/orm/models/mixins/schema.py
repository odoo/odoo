"""
Database schema management mixin for ORM models.

SchemaMixin Methods:
- _parent_store_compute: Compute parent_path field from scratch
- _check_removed_columns: Check for columns to drop NOT NULL constraints
- _init_column: Initialize column values for existing rows
- _table_has_rows: Check if the model's table has rows
- _auto_init: Initialize database schema
- init: Hook for custom schema modifications
- _check_parent_path: Validate parent_path field configuration
- _add_sql_constraints: Apply SQL constraints to database
- _sql_error_to_message: Convert SQL errors to user messages
- _sql_error_to_message_generic: Generic SQL error message conversion

Table object classes are defined in ``odoo.orm.models.table_objects``.
"""

import logging
import typing

import psycopg
import psycopg.errors

from odoo.tools import SQL, format_list, ormcache, sql

from ... import decorators as api
from ...helpers import get_columns_from_sql_diagnostics
from ...validation import raise_on_invalid_object_name

_logger = logging.getLogger("odoo.models")


class SchemaMixin:
    """Mixin providing database schema management functionality.

    This mixin is inherited by BaseModel and provides methods for managing
    the database schema of models, including table creation, column initialization,
    constraint management, and SQL error handling.
    """

    __slots__ = ()

    # Type hints for attributes provided by BaseModel (runtime)
    _fields: dict
    _table: str
    _name: str
    _description: str
    _abstract: bool
    _auto: bool
    _parent_store: bool
    _parent_name: str
    _table_objects: dict
    env: typing.Any
    id: int

    def _parent_store_compute(self) -> None:
        """Compute parent_path field from scratch."""
        if not self._parent_store:
            return

        # Each record is associated to a string 'parent_path', that represents
        # the path from the record's root node to the record. The path is made
        # of the node ids suffixed with a slash (see example below). The nodes
        # in the subtree of record are the ones where 'parent_path' starts with
        # the 'parent_path' of record.
        #
        #               a                 node | id | parent_path
        #              / \                  a  | 42 | 42/
        #            ...  b                 b  | 63 | 42/63/
        #                / \                c  | 84 | 42/63/84/
        #               c   d               d  | 85 | 42/63/85/
        #
        # Note: the final '/' is necessary to match subtrees correctly: '42/63'
        # is a prefix of '42/630', but '42/63/' is not a prefix of '42/630/'.
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
        self.invalidate_model(["parent_path"])

    def _check_removed_columns(self, log: bool = False) -> None:
        if self._abstract:
            return
        # iterate on the database columns to drop the NOT NULL constraints of
        # fields which were required but have been removed (or will be added by
        # another module)
        cr = self.env.cr
        cols = {name for name, field in self._fields.items() if field.is_column}
        for col_name, col_data in sql.table_columns(cr, self._table).items():
            if col_name in cols:
                continue
            if log:
                _logger.debug(
                    "column %s is in the table %s but not in the corresponding object %s",
                    col_name,
                    self._table,
                    self._name,
                )
            if col_data["is_nullable"] == "NO":
                sql.drop_not_null(cr, self._table, col_name)

    def _init_column(self, column_name: str) -> None:
        """Initialize the value of the given column for existing rows."""
        # get the default value; ideally, we should use default_get(), but it
        # fails due to ir.default not being ready
        field = self._fields[column_name]
        if field.default:
            value = field.default(self)
            value = field.convert_to_write(value, self)
            value = field.convert_to_column_insert(value, self)
        else:
            value = None
        # Write value if non-NULL, except for booleans for which False means
        # the same as NULL - this saves us an expensive query on large tables,
        # if the boolean is required we still write False to allow NOT NULL constraints.
        necessary = (
            (value is not None) if field.type != "boolean" or field.required else value
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
                    "UPDATE %(table)s SET %(field)s = %(value)s WHERE %(field)s IS NULL",
                    table=SQL.identifier(self._table),
                    field=SQL.identifier(column_name),
                    value=value,
                )
            )

    @ormcache()
    def _table_has_rows(self) -> bool:
        """Return whether the model's table has rows. This method should only
        be used when updating the database schema (:meth:`~._auto_init`).
        """
        self.env.cr.execute(
            SQL("SELECT 1 FROM %s LIMIT 1", SQL.identifier(self._table))
        )
        return bool(self.env.cr.rowcount)

    def _auto_init(self) -> None:
        """Initialize the database schema of ``self``:
        - create the corresponding table,
        - create/update the necessary columns/tables for fields,
        - initialize new columns on existing rows,
        - add the SQL constraints given on the model,
        - add the indexes on indexed fields,

        Also prepare post-init stuff to:
        - add foreign key constraints,
        - reflect models, fields, relations and constraints,
        - mark fields to recompute on existing records.

        Note: you should not override this method. Instead, you can modify
        the model's database schema by overriding method :meth:`~.init`,
        which is called right after this one.
        """
        raise_on_invalid_object_name(self._name)

        # This prevents anything called by this method (in particular default
        # values) from prefetching a field for which the corresponding column
        # has not been added in database yet!
        self = self.with_context(prefetch_fields=False)

        cr = self.env.cr
        update_custom_fields = self.env.context.get("update_custom_fields", False)
        must_create_table = not sql.table_exists(cr, self._table)
        parent_path_compute = False

        if self._auto:
            if must_create_table:

                def make_type(field):
                    return field.column_type[1] + (
                        " NOT NULL" if field.required else ""
                    )

                sql.create_model_table(
                    cr,
                    self._table,
                    self._description,
                    [
                        (field.name, make_type(field), field.string)
                        for field in sorted(
                            self._fields.values(), key=lambda f: f.column_order
                        )
                        if field.name != "id" and field.is_column
                    ],
                )

            if self._parent_store:
                if not sql.column_exists(cr, self._table, "parent_path"):
                    sql.create_column(
                        self.env.cr, self._table, "parent_path", "VARCHAR"
                    )
                    parent_path_compute = True
                self._check_parent_path()

            if not must_create_table:
                self._check_removed_columns(log=False)

            # update the database schema for fields
            columns = sql.table_columns(cr, self._table)
            fields_to_compute = []

            for field in sorted(self._fields.values(), key=lambda f: f.column_order):
                if not field.store:
                    continue
                if field.manual and not update_custom_fields:
                    continue  # don't update custom fields
                new = field.update_db(self, columns)
                if new and field.compute:
                    fields_to_compute.append(field)

            if fields_to_compute:
                # mark existing records for computation now, so that computed
                # required fields are flushed before the NOT NULL constraint is
                # added to the database
                cr.execute(SQL("SELECT id FROM %s", SQL.identifier(self._table)))
                records = self.browse(row[0] for row in cr.fetchall())
                if records:
                    for field in fields_to_compute:
                        _logger.info("Prepare computation of %s", field)
                        self.env.add_to_compute(field, records)

        if self._auto:
            self._add_sql_constraints()

        if parent_path_compute:
            self._parent_store_compute()

    @api.private
    def init(self) -> None:
        """This method is called after :meth:`~._auto_init`, and may be
        overridden to create or modify a model's database schema.
        """

    def _check_parent_path(self) -> None:
        field = self._fields.get("parent_path")
        if field is None:
            _logger.error(
                "add a field parent_path on model %r: `parent_path = fields.Char(index=True)`.",
                self._name,
            )
        elif not field.index:
            _logger.error(
                "parent_path field on model %r should be indexed! Add index=True to the field definition.",
                self._name,
            )

    def _add_sql_constraints(self) -> None:
        """Modify this model's database table objects so they match the one
        in _table_objects.
        """
        for obj in self._table_objects.values():
            obj.apply_to_database(self)

    @api.model
    def _sql_error_to_message(self, exc: psycopg.Error) -> str:
        """Convert a database exception to a user error message depending on the model.

        Note that the cursor on self has to be in a valid state.
        """
        if (constraint_name := exc.diag.constraint_name) and (
            cons := self._table_objects.get(constraint_name)
        ):
            cons_rec = (
                self.env["ir.model.constraint"]
                .sudo()
                .search_fetch(
                    [
                        ("name", "=", constraint_name),
                        ("model.model", "=", self._name),
                    ],
                    ["message"],
                    limit=1,
                )
            )
            if message := cons_rec.message:
                return message
            # get the message from the object
            if message := cons.get_error_message(self, exc.diag):
                return message
        return self._sql_error_to_message_generic(exc)

    @api.model
    def _sql_error_to_message_generic(self, exc: psycopg.Error) -> str:
        """Convert a database exception to a generic user error message."""
        diag = exc.diag
        unknown = self.env._("Unknown")
        model_string = self.env["ir.model"]._get(self._name).name or self._description
        info = {
            "model_display": f"'{model_string}' ({self._name})",
            "table_name": diag.table_name,
            "constraint_name": diag.constraint_name,
        }
        if self._table == diag.table_name:
            columns = get_columns_from_sql_diagnostics(
                self.env.cr, diag, check_registry=True
            )
        else:
            columns = get_columns_from_sql_diagnostics(self.env.cr, diag)
            info["model_display"] = unknown
        if not columns:
            info["field_display"] = unknown
        elif len(columns) == 1 and (field := self._fields.get(columns[0])):
            field_string = field._description_string(self.env)
            info["field_display"] = f"'{field_string}' ({field.name})"
        else:
            info["field_display"] = f"'{format_list(self.env, columns)}'"

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
            info["detail"] = diag.message_detail  # contains conflicting key and value
            return self.env._(
                "The value for %(field_display)s already exists.\n\nDetail: %(detail)s\n",
                **info,
            )

        # No good message can be created for psycopg.errors.CheckViolation

        # fallback
        return str(exc)
