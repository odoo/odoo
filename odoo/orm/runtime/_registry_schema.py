import logging
import typing
import warnings
from collections.abc import Callable, Iterable

import psycopg

from odoo.db import FunctionStatus
from odoo.db import schema as sql
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import get_index_name
from odoo.tools import OrderedSet

from ..primitives import SUPERUSER_ID
from ._registry_stubs import _RegistryStubs

if typing.TYPE_CHECKING:
    from odoo.db import BaseCursor, Cursor
    from odoo.fields import Field
    from odoo.models import BaseModel
    from odoo.orm._typing import ModelLike


_logger = logging.getLogger("odoo.registry")
_schema = logging.getLogger("odoo.schema")
_debug = DebugLog(__name__)


class _RegistrySchemaMixin(_RegistryStubs):
    _ordinary_tables: dict[str, bool]
    _constraint_queue: dict[typing.Any, Callable[[BaseCursor], None]]
    not_null_fields: set[Field]
    not_null_columns: set[tuple[str, str]]

    database_translated_fields: dict[str, str]
    database_company_dependent_fields: set[str]

    def _init_schema_state(self) -> None:
        self._ordinary_tables = {}
        self._constraint_queue = {}
        self.not_null_fields = set()
        self.not_null_columns = set()
        self.database_translated_fields = {}
        self.database_company_dependent_fields = set()

    def reflect_database_fields(self, cr: BaseCursor) -> None:
        cr.execute(
            "SELECT model || '.' || name, translate FROM ir_model_fields "
            "WHERE translate IS NOT NULL"
        )
        self.database_translated_fields = dict(cr.fetchall())
        if sql.column_exists(cr, "ir_model_fields", "company_dependent"):
            cr.execute(
                "SELECT model || '.' || name FROM ir_model_fields "
                "WHERE company_dependent IS TRUE"
            )
            self.database_company_dependent_fields = {row[0] for row in cr.fetchall()}

    def take_database_translated_fields(self) -> dict[str, str]:
        taken = self.database_translated_fields
        self.database_translated_fields = {}
        return taken

    def post_constraint(
        self, cr: BaseCursor, func: Callable[[BaseCursor], None], key
    ) -> None:
        try:
            if key not in self._constraint_queue:
                with cr.savepoint(flush=False):
                    func(cr)
            else:
                _debug.logic("registry.constraint.requeued", key=key)
                self._constraint_queue[key] = func
        except Exception as e:
            _debug.logic(
                "registry.constraint.failed",
                key=key,
                install=self.init_phase.install,
                error=type(e).__name__,
            )
            if self.init_phase.install:
                _schema.error("%s", e)
            else:
                _schema.info("%s", e)
                self._constraint_queue[key] = func

    def finalize_constraints(self, cr: Cursor) -> None:
        _debug.pipeline(
            "registry.finalize_constraints", queued=len(self._constraint_queue)
        )
        for func in self._constraint_queue.values():
            try:
                with cr.savepoint(flush=False):
                    func(cr)
            except Exception as e:
                _schema.warning("%s", e)
        self._constraint_queue.clear()

    def check_null_constraints(self, cr: Cursor) -> None:
        cr.execute("""
            SELECT c.relname, a.attname
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = current_schema
            AND a.attnotnull = true
            AND a.attnum > 0
            AND a.attname != 'id';
        """)
        self.not_null_columns = set(cr.fetchall())
        self.rebuild_not_null_fields(warn=True)
        _debug.perf.count(
            "registry.null_constraints_checked",
            columns=len(self.not_null_columns),
            fields=len(self.not_null_fields),
        )

    def rebuild_not_null_fields(self, *, warn: bool = False) -> None:
        # the set holds Field objects, which setup_models recreates; rebuild it from
        # the reflected columns so a re-setup never leaves it pointing at dead fields
        self.not_null_fields.clear()
        for Model in self.models.values():
            if Model._auto and not Model._abstract:
                for field_name, field in Model._fields.items():
                    if field_name == "id":
                        self.not_null_fields.add(field)
                        continue
                    if field.column_type and field.store and field.required:
                        if (Model._table, field_name) in self.not_null_columns:
                            self.not_null_fields.add(field)
                        elif warn:
                            _schema.warning("Missing not-null constraint on %s", field)

    def _get_index_expression(self, field, index) -> tuple[str, str, str]:
        column_expression = f'"{field.name}"'
        if index == "trigram":
            if field.translate:
                column_expression = (
                    f"""(jsonb_path_query_array({column_expression}, '$.*')::text)"""
                )
            if self.has_unaccent == FunctionStatus.INDEXABLE:
                column_expression = self.unaccent(column_expression)
            elif self.has_unaccent:
                warnings.warn(
                    "PostgreSQL function 'unaccent' is present but not immutable, "
                    "therefore trigram indexes may not be effective.",
                    stacklevel=1,
                )
            expression = f"{column_expression} gin_trgm_ops"
            method = "gin"
            where = ""
        elif index == "btree_not_null" and field.company_dependent:
            expression = f"({column_expression} IS NOT NULL)"
            method = "btree"
            where = f"{column_expression} IS NOT NULL"
        else:
            expression = f"{column_expression}"
            method = "btree"
            where = (
                f"{column_expression} IS NOT NULL" if index == "btree_not_null" else ""
            )
        return expression, method, where

    def _apply_index(
        self,
        cr: Cursor,
        indexname: str,
        tablename: str,
        expression: str,
        method: str,
        where: str,
        stale: bool,
    ) -> None:
        try:
            with cr.savepoint(flush=False):
                if stale:
                    _debug.logic(
                        "registry.index.stale_dropped",
                        index=indexname,
                        table=tablename,
                    )
                    sql.drop_index(cr, indexname, tablename)
                sql.create_index(
                    cr,
                    indexname,
                    tablename,
                    [expression],
                    method,
                    where,
                    check_exists=False,
                )
        except psycopg.DatabaseError:
            _schema.error("Unable to add index %r for %s", indexname, self)

    def check_indexes(self, cr: Cursor, model_names: Iterable[str]) -> None:
        model_names = list(model_names)
        expected = [
            (get_index_name(Model._table, field.name), Model._table, field)
            for model_name in model_names
            for Model in [self.models[model_name]]
            if Model._auto and not Model._abstract
            for field in Model._fields.values()
            if field.column_type and field.store
        ]
        if not expected:
            return

        cr.execute(
            """
            SELECT idx.relname, tbl.relname, am.amname,
                   ix.indpred IS NOT NULL AS has_predicate
              FROM pg_index ix
              JOIN pg_class idx ON idx.oid = ix.indexrelid
              JOIN pg_class tbl ON tbl.oid = ix.indrelid
              JOIN pg_am am ON am.oid = idx.relam
             WHERE idx.relname = ANY(%s)
               AND idx.relnamespace = current_schema::regnamespace
            """,
            [[row[0] for row in expected]],
        )
        existing = {
            indexname: (tablename, method, has_predicate)
            for indexname, tablename, method, has_predicate in cr.fetchall()
        }
        _debug.pipeline(
            "registry.check_indexes",
            models=len(model_names),
            expected=len(expected),
            existing=len(existing),
        )

        for indexname, tablename, field in expected:
            index = field.index
            if index not in ("btree", "btree_not_null", "trigram", True, False, None):
                raise ValueError(
                    f"Invalid index value {index!r} on {field}; allowed values: "
                    f"'btree', 'btree_not_null', 'trigram', True, False, None"
                )

            if index and field.translate and index != "trigram":
                _schema.warning(
                    f"Index attribute on {field!r} ignored, only trigram index is supported for translated fields"
                )
                continue

            will_index = bool(index) and (
                (not field.translate and index != "trigram")
                or (index == "trigram" and self.has_trigram)
            )
            if indexname in existing:
                expected_method = "gin" if index == "trigram" else "btree"
                expected_predicate = index == "btree_not_null"
                _table, actual_method, actual_predicate = existing[indexname]
                stale = (
                    actual_method != expected_method
                    or bool(actual_predicate) != expected_predicate
                )
                will_index = will_index and stale
            else:
                stale = False

            if will_index:
                expression, method, where = self._get_index_expression(field, index)
                self._apply_index(
                    cr, indexname, tablename, expression, method, where, stale
                )

            elif (
                not index
                and tablename == existing.get(indexname, (None, None, None))[0]
            ):
                _schema.info(
                    "Keep unexpected index %s on table %s", indexname, tablename
                )

    def add_foreign_key(
        self,
        table1: str,
        column1: str,
        table2: str,
        column2: str,
        ondelete: str,
        model: BaseModel,
        module: str | None,
        force: bool = True,
    ) -> None:
        key = (table1, column1)
        val = (table2, column2, ondelete, model, module)
        foreign_keys = self.init_phase.foreign_keys
        if force:
            foreign_keys[key] = val
        else:
            foreign_keys.setdefault(key, val)

    def check_foreign_keys(self, cr: Cursor) -> None:
        foreign_keys = self.init_phase.foreign_keys
        if not foreign_keys:
            return

        tablenames = {table for table, column in foreign_keys}
        existing = {
            (table1, column1): (name, table2, column2, deltype)
            for name, table1, column1, table2, column2, deltype in sql.get_fk_constraints_batch(
                cr, tablenames
            )
        }

        _debug.pipeline(
            "registry.check_foreign_keys",
            declared=len(foreign_keys),
            existing=len(existing),
            tables=len(tablenames),
        )
        for key, val in foreign_keys.items():
            table1, column1 = key
            table2, column2, ondelete, model, module = val
            deltype = sql._CONFDELTYPES[ondelete.upper()]
            spec = existing.get(key)
            if spec is not None:
                if (spec[1], spec[2], spec[3]) == (table2, column2, deltype):
                    continue
                sql.drop_constraint(cr, table1, spec[0])
            _debug.logic(
                "registry.foreign_key.added"
                if spec is None
                else "registry.foreign_key.replaced",
                table=table1,
                column=column1,
                target=table2,
                ondelete=ondelete,
                previous=None if spec is None else spec[0],
            )
            sql.add_foreign_key(cr, table1, column1, table2, column2, ondelete)
            conname = sql.get_fk_constraint_names(
                cr, table1, column1, table2, column2, ondelete
            )[0]
            model.env.registry.metaschema.reflect_constraint(
                model, conname, "f", None, module
            )

    def check_tables_exist(self, cr: Cursor) -> None:
        from .environment import Environment

        env = Environment(cr, SUPERUSER_ID, {})
        table2model = {
            model._table: name
            for name, model in env.registry.items()
            if not model._abstract and not model._table_query
        }
        missing_tables = set(table2model).difference(
            sql.get_tables_existing(cr, table2model)
        )

        _debug.pipeline(
            "registry.check_tables_exist",
            tables=len(table2model),
            missing=len(missing_tables),
        )
        if missing_tables:
            missing = {table2model[table] for table in missing_tables}
            _logger.info("Models have no table: %s.", ", ".join(missing))
            for name in missing:
                _logger.info("Recreate table of model %s.", name)
                env[name]._auto_init()
                env[name].init()
            env.flush_all()
            missing_tables = set(table2model).difference(
                sql.get_tables_existing(cr, table2model)
            )
            for table in missing_tables:
                _logger.error("Model %s has no table.", table2model[table])

    def is_an_ordinary_table(self, model: ModelLike) -> bool:
        table = model._table
        if (known := self._ordinary_tables.get(table)) is not None:
            return known

        cr = model.env.cr
        tables = OrderedSet(m._table for m in self.models.values())
        tables.add(table)
        cr.execute(
            """
                SELECT c.relname
                  FROM pg_class c
                  JOIN pg_namespace n ON (n.oid = c.relnamespace)
                 WHERE c.relname = ANY(%s)
                   AND c.relkind = 'r'
                   AND n.nspname = current_schema
            """,
            [list(tables)],
        )
        ordinary = {row[0] for row in cr.fetchall()}
        self._ordinary_tables.update({t: t in ordinary for t in tables})
        return table in ordinary
