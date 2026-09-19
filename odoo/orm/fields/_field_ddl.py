import logging
import typing

from odoo.db import schema as sql
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, ModelLike
    from .base import Field
    from .relational import Many2many, Many2one
    from .textual import BaseString, Char

_logger = logging.getLogger("odoo.fields")
_debug = DebugLog(__name__)
_schema = logging.getLogger("odoo.schema")


def get_column_order(udt_name: str) -> int:
    return sql.SQL_ORDER_BY_TYPE[udt_name]


def update_db(
    field: Field, model: ModelLike, columns: dict[str, dict[str, typing.Any]]
) -> bool:
    if not field.column_type:
        return False

    column = columns.get(field.name) or {}

    field.update_db_column(model, column)
    field.update_db_notnull(model, column)

    if (
        not column
        and field.related
        and field.related.count(".") == 1
        and field.related_field.store
        and not field.related_field.compute
        and not field.related_field.is_attachment_backed
        and not field.related_field.is_x2many
    ):
        join_field = model._fields[field._related_names[0]]
        if join_field.is_many2one and join_field.store and not join_field.compute:
            _debug.logic(
                "field.ddl.related_column_filled_by_join",
                model=model._name,
                field=field.name,
                related=field.related,
            )
            model.pool.post_init(field.update_db_related, model)
            return False

    return not column


def update_db_column(
    field: Field, model: ModelLike, column: dict[str, typing.Any]
) -> None:
    column_type = field.column_type
    if column_type is None:
        raise TypeError(f"{field} has no column: update_db_column does not apply")
    if not column:
        sql.create_column(
            model.env.cr,
            model._table,
            field.name,
            column_type[1],
            field.string,
        )
        return
    if column["udt_name"] == column_type[0]:
        return
    _debug.logic(
        "field.ddl.column_converted",
        model=model._name,
        field=field.name,
        from_type=column["udt_name"],
        to_type=column_type[0],
    )
    field._convert_db_column(model, column)


def convert_db_column(
    field: Field, model: ModelLike, column: dict[str, typing.Any]
) -> None:
    column_type = field.column_type
    if column_type is None:
        raise TypeError(f"{field} has no column: _convert_db_column does not apply")
    sql.convert_column(model.env.cr, model._table, field.name, column_type[1])


def convert_db_column_translatable(
    field: BaseString, model: ModelLike, column: dict[str, typing.Any]
) -> None:
    assert field.column_type is not None, (
        f"{field}: a column conversion is only reached for a stored column"
    )
    _debug.logic(
        "field.ddl.column_converted_translatable",
        model=model._name,
        field=field.name,
        from_type=column["udt_name"],
        translate=bool(field.translate),
    )
    if field.translate or column["udt_name"] == "jsonb":
        sql.convert_column_translatable(
            model.env.cr, model._table, field.name, field.column_type[1]
        )
    else:
        sql.convert_column(model.env.cr, model._table, field.name, field.column_type[1])


def widen_varchar_column(
    field: Char, model: ModelLike, column: dict[str, typing.Any]
) -> None:
    column_type = field.column_type
    if (
        column
        and column_type is not None
        and column_type[0] == "varchar"
        and column["udt_name"] == "varchar"
        and column["character_maximum_length"]
        and (field.size is None or column["character_maximum_length"] < field.size)
    ):
        _debug.logic(
            "field.ddl.varchar_widened",
            model=model._name,
            field=field.name,
            from_size=column["character_maximum_length"],
            to_size=field.size,
        )
        sql.convert_column(model.env.cr, model._table, field.name, column_type[1])


def update_db_notnull(
    field: Field, model: ModelLike, column: dict[str, typing.Any]
) -> None:
    has_notnull = column and column["is_nullable"] == "NO"

    if not column or (field.required and not has_notnull):
        if model._has_rows_in_table():
            _debug.pipeline(
                "field.ddl.init_column",
                model=model._name,
                field=field.name,
                new_column=not column,
            )
            model._init_column(field.name, new_column=not column)

    if field.required and not has_notnull:
        _debug.logic(
            "field.ddl.not_null_scheduled",
            model=model._name,
            field=field.name,
            new_column=not column,
            computed=bool(field.compute),
        )

        @model.pool.post_init
        def add_not_null():
            current = model._fields[field.name]
            if not current.required or not current.store:
                return
            if current.compute:
                records = model.browse(
                    id_
                    for (id_,) in model.env.execute_query(
                        SQL(
                            "SELECT id FROM %s AS t WHERE %s IS NULL",
                            SQL.identifier(model._table),
                            model._field_to_sql("t", current.name),
                        )
                    )
                )
                model.env.add_to_compute(current, records)
            model.flush_model([current.name])

            sql_default = None
            if (
                current.default
                and not current.translate
                and not current.company_dependent
            ):
                try:
                    value = current.default(model.browse())
                    if isinstance(value, (str, int, float, bool)):
                        sql_default = current.convert_to_column(
                            value, model, validate=False
                        )
                except Exception:
                    _logger.debug(
                        "Could not derive a SQL DEFAULT for %s; "
                        "applying NOT NULL without one",
                        current,
                        exc_info=True,
                    )

            def apply_not_null(cr):
                sql.set_not_null(cr, model._table, current.name)

            model.pool.post_constraint(
                model.env.cr,
                apply_not_null,
                key=f"add_not_null:{model._table}:{current.name}",
            )

            if sql_default is not None:

                def apply_default(cr, sql_default=sql_default):
                    sql.set_default(cr, model._table, current.name, sql_default)

                model.pool.post_constraint(
                    model.env.cr,
                    apply_default,
                    key=f"set_default:{model._table}:{current.name}",
                )

    elif not field.required and has_notnull:
        _debug.logic("field.ddl.not_null_dropped", model=model._name, field=field.name)
        sql.drop_not_null(model.env.cr, model._table, field.name)


def update_db_related(field: Field, model: ModelLike) -> None:
    comodel = model.env[field.related_field.model_name]
    join_field, comodel_field = field._related_names
    with _debug.perf(
        "field.ddl.related_column_filled",
        cr=model.env.cr,
        model=model._name,
        field=field.name,
        comodel=comodel._name,
    ) as span:
        model.env.cr.execute(
            SQL(
                """ UPDATE %(model_table)s AS x
                SET %(model_field)s = y.%(comodel_field)s
                FROM %(comodel_table)s AS y
                WHERE x.%(join_field)s = y.id """,
                model_table=SQL.identifier(model._table),
                model_field=SQL.identifier(field.name),
                comodel_table=SQL.identifier(comodel._table),
                comodel_field=SQL.identifier(comodel_field),
                join_field=SQL.identifier(join_field),
            )
        )
        span.set(rows=model.env.cr.rowcount)


def update_db_foreign_key(
    field: Many2one, model: BaseModel, column: dict[str, typing.Any]
) -> None:
    if field.company_dependent:
        return
    comodel = model.env[field.comodel_name]
    if not model._is_an_ordinary_table() or not comodel._is_an_ordinary_table():
        _debug.logic(
            "field.ddl.foreign_key_skipped",
            model=model._name,
            field=field.name,
            reason="not_ordinary_table",
        )
        return
    if not comodel._auto or comodel._is_table_inheritance_root():
        _debug.logic(
            "field.ddl.foreign_key_skipped",
            model=model._name,
            field=field.name,
            reason="comodel_not_auto" if not comodel._auto else "inheritance_root",
        )
        return
    model.pool.add_foreign_key(
        model._table,
        field.name,
        comodel._table,
        "id",
        field.ondelete or "set null",
        model,
        field._module,
    )


def update_db_relation_table(field: Many2many, model: ModelLike) -> bool:
    cr = model.env.cr
    relation, column1, column2 = field._get_relation_triple()
    # An explicit relation may be a model with its own payload and constraints.
    # Its model owns table creation, foreign keys and uninstall reflection even
    # when this referencing model happens to initialize first.
    if not model.pool.register_relation_table(
        model._name, relation, field._module, reflect=not field.manual
    ):
        return False
    comodel = model.env[field.comodel_name]
    if not sql.table_exists(cr, relation):
        cr.execute(
            SQL(
                """ CREATE TABLE %(rel)s (%(id1)s INTEGER NOT NULL,
                                      %(id2)s INTEGER NOT NULL,
                                      PRIMARY KEY(%(id1)s, %(id2)s));
                COMMENT ON TABLE %(rel)s IS %(comment)s;
                CREATE INDEX ON %(rel)s (%(id2)s, %(id1)s); """,
                rel=SQL.identifier(relation),
                id1=SQL.identifier(column1),
                id2=SQL.identifier(column2),
                comment=f"RELATION BETWEEN {model._table} AND {comodel._table}",
            )
        )
        _schema.debug(
            "Create table %r: m2m relation between %r and %r",
            relation,
            model._table,
            comodel._table,
        )
        _debug.lifecycle(
            "field.ddl.relation_table_created",
            model=model._name,
            field=field.name,
            relation=relation,
        )
        model.pool.post_init(field.update_db_foreign_keys, model)
        return True

    model.pool.post_init(field.update_db_foreign_keys, model)
    return False


def _relation_is_shared_with_tree(field: Many2many, model: BaseModel) -> bool:
    if not model._table_inheritance_root:
        return False
    if model._is_table_inheritance_root():
        return True
    root = model.env[model._get_root_model_name()]
    root_field = root._fields.get(field.name)
    return root_field is not None and root_field.relation == field.relation


def update_db_foreign_keys(field: Many2many, model: BaseModel) -> None:
    comodel = model.env[field.comodel_name]
    relation, column1, column2 = field._get_relation_triple()
    model_side = model._is_an_ordinary_table() and not _relation_is_shared_with_tree(
        field, model
    )
    _debug.pipeline(
        "field.ddl.m2m_foreign_keys",
        model=model._name,
        field=field.name,
        relation=relation,
        model_side=model_side,
        comodel_side=comodel._is_an_ordinary_table()
        and not comodel._is_table_inheritance_root(),
        ondelete=field.ondelete or "cascade",
    )
    if model_side:
        model.pool.add_foreign_key(
            relation,
            column1,
            model._table,
            "id",
            "cascade",
            model,
            field._module,
            force=False,
        )
    if comodel._is_an_ordinary_table() and not comodel._is_table_inheritance_root():
        model.pool.add_foreign_key(
            relation,
            column2,
            comodel._table,
            "id",
            field.ondelete or "cascade",
            model,
            field._module,
        )
