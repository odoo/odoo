import logging
import typing
from collections import defaultdict
from contextlib import contextmanager, suppress
from datetime import datetime
from typing import TYPE_CHECKING, Any

from dateutil.relativedelta import relativedelta
from psycopg.errors import InsufficientPrivilege

from odoo.fields import Field, Many2one
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import SQL

if TYPE_CHECKING:
    from collections.abc import Generator

    from odoo.api import Environment
    from odoo.models import Model

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

MIN_DATETIME = datetime((datetime.now() - relativedelta(years=4)).year, 1, 1)
MAX_DATETIME = datetime.now()


def get_field_variation_date(
    model: Model, field: Field, factor: int, series_alias: str
) -> SQL:
    total_days = min((MAX_DATETIME - MIN_DATETIME).days, factor)
    assert field._column_type is not None
    cast_type = SQL(field._column_type[1])

    def redistribute(value: SQL) -> SQL:
        return SQL(
            "(%(value)s - (%(factor)s - %(series_alias)s) * (%(total_days)s::float/%(factor)s) * interval '1 days')::%(cast_type)s",
            value=value,
            factor=factor,
            series_alias=SQL.identifier(series_alias),
            total_days=total_days,
            cast_type=cast_type,
        )

    if not field.company_dependent:
        return redistribute(SQL.identifier(field.name))
    return SQL(
        "(SELECT jsonb_object_agg(key, %(expr)s) FROM jsonb_each_text(%(field)s))",
        expr=redistribute(SQL("value::%s", cast_type)),
        field=SQL.identifier(field.name),
    )


def get_field_variation_char(field: Field, postfix: str | SQL | None = None) -> SQL:
    if postfix is None:
        return SQL.identifier(field.name)
    if not isinstance(postfix, SQL):
        postfix = SQL.identifier(postfix)
    if field.translate:
        return SQL(
            """(
            SELECT jsonb_object_agg(key, value || %(postfix)s)
            FROM jsonb_each_text(%(field)s)
        )""",
            field=SQL.identifier(field.name),
            postfix=postfix,
        )
    else:
        return SQL(
            """
            CASE
                WHEN %(field)s IS NULL OR %(field)s IN ('/', '')
                THEN %(field)s
                ELSE %(field)s || %(postfix)s
            END
        """,
            field=SQL.identifier(field.name),
            postfix=postfix,
        )


class PopulateContext:
    def __init__(self) -> None:
        self.has_session_replication_role: bool = True

    @staticmethod
    def _restore_indexes(model: Model, indexes: list[dict]) -> None:
        _logger.info("Adding indexes back on table %s...", model._table)
        with _debug.perf(
            "populate.indexes_restored",
            cr=model.env.cr,
            table=model._table,
            indexes=len(indexes),
        ):
            for index in indexes:
                try:
                    with model.env.cr.savepoint():
                        model.env.cr.execute(index["definition"])  # noqa: E8501  pg_indexes.indexdef, read back from the catalog
                except Exception:
                    _logger.exception(
                        "Could not restore index %s on %s; the table is left "
                        "without it",
                        index["name"],
                        model._table,
                    )
                    _debug.logic(
                        "populate.index_restore_failed",
                        table=model._table,
                        index=index["name"],
                    )

    @contextmanager
    def ignore_indexes(self, model: Model) -> Generator[None]:
        indexes = model.env.execute_query_dict(
            SQL(
                """
            SELECT indexname AS name, indexdef AS definition
              FROM pg_indexes
             WHERE tablename = %s
               AND schemaname = current_schema
               AND indexname NOT LIKE %s
               AND indexdef NOT LIKE %s
             ORDER BY indexname
        """,
                model._table,
                "%pkey",
                "%UNIQUE%",
            )
        )
        _debug.logic(
            "populate.indexes_dropped", table=model._table, indexes=len(indexes)
        )
        if indexes:
            _logger.info("Dropping indexes on table %s...", model._table)
            for index in indexes:
                model.env.cr.execute(
                    SQL("DROP INDEX %s CASCADE", SQL.identifier(index["name"]))
                )
            try:
                yield
            finally:
                # on an aborted transaction nothing can be restored, and the
                # rollback that follows puts the dropped indexes back itself
                if model.env.cr.in_failed_transaction():
                    _debug.logic(
                        "populate.indexes_left_to_rollback", table=model._table
                    )
                else:
                    self._restore_indexes(model, indexes)
        else:
            yield

    @contextmanager
    def ignore_fkey_constraints(self, model: Model) -> Generator[None]:
        if not self.has_session_replication_role:
            yield
            return
        try:
            with model.env.cr.savepoint():
                model.env.cr.execute("SET session_replication_role TO replica")
        except InsufficientPrivilege:
            _logger.warning(
                "Cannot ignore Fkey constraints during insertion due to "
                "insufficient privileges for current pg_role. Retrying without "
                "dropping the FK constraint check; the bulk insertion will be "
                "vastly slower than anticipated."
            )
            self.has_session_replication_role = False
            _debug.logic("populate.fkey_checks_kept", table=model._table)
            yield
            return
        try:
            yield
        finally:
            with suppress(Exception):
                model.env.cr.execute("RESET session_replication_role")


def unique_indexed_columns(model: Model) -> frozenset[str]:
    query = SQL(
        """
        SELECT DISTINCT a.attname
          FROM pg_index idx
               JOIN pg_class t ON t.oid = idx.indrelid
               JOIN pg_attribute a ON a.attnum = ANY (idx.indkey) AND a.attrelid = t.oid
         WHERE t.relname = %s
           AND t.relnamespace = current_schema::regnamespace
           AND idx.indisunique = TRUE
    """,
        model._table,
    )
    return frozenset(row[0] for row in model.env.execute_query(query))


def is_field_variation_required(
    model: Model, field: Field, unique_columns: frozenset[str] | None = None
) -> bool:
    in_names_search = model._rec_names_search and field.name in model._rec_names_search
    in_name = model._rec_name and field.name == model._rec_name
    if (in_name or in_names_search) and field.type != "many2one":
        return True
    if field.type in ("date", "datetime"):
        return True
    if field.index == "trigram":
        return True
    if unique_columns is None:
        unique_columns = unique_indexed_columns(model)
    return field.name in unique_columns


def get_field_variation(
    model: Model, field: Field, factor: int, series_alias: str
) -> SQL:
    match field.type:
        case "char" | "text":
            return get_field_variation_char(field, postfix=series_alias)
        case "date" | "datetime":
            return get_field_variation_date(model, field, factor, series_alias)
        case "html":
            return SQL.identifier(field.name)
        case _:
            _logger.warning(
                "The field %s of type %s was marked to be varied, "
                "but no variation branch was found! Defaulting to a raw copy.",
                field,
                field.type,
            )
            _debug.logic(
                "populate.variation_unsupported",
                model=model._name,
                field=field.name,
                type=field.type,
            )
            return SQL.identifier(field.name)


def _id_table(model: Model) -> str:
    return model._table_inheritance_root or model._table


def get_last_id(model: Model) -> int:
    query = SQL(
        "SELECT COALESCE(MAX(id), 0) FROM %s",
        SQL.identifier(_id_table(model)),
    )
    return model.env.execute_query(query)[0][0]


def _tree_members(model: Model) -> list[Model]:
    root = model._table_inheritance_root
    if not root or model._table != root:
        return [model]
    by_table: dict[str, Model] = {root: model}
    names = model.env.registry.model_names_by_inheritance_root.get(root, ())
    members = [typing.cast("Model", model.env[name]) for name in names]
    for member in sorted(
        members, key=lambda m: (m._table != m._name.replace(".", "_"), m._name)
    ):
        if member._auto and member._is_an_ordinary_table():
            by_table.setdefault(member._table, member)
    return list(by_table.values())


def populate_field(
    model: Model,
    field: Field,
    populated: dict[Model, int],
    factors: dict[Model, int],
    table_alias: str = "t",
    series_alias: str = "s",
    unique_columns: frozenset[str] | None = None,
    id_offset: int | None = None,
) -> SQL | None:

    def copy_raw(field_: Field) -> SQL:
        return SQL.identifier(field_.name)

    def copy(field_: Field) -> SQL:
        if is_field_variation_required(model, field_, unique_columns):
            return get_field_variation(model, field_, factors[model], series_alias)
        else:
            return copy_raw(field_)

    def copy_id() -> SQL:
        last_id = get_last_id(model) if id_offset is None else id_offset
        populated[model] = last_id
        return SQL(
            "id + %(last_id)s * %(series_alias)s",
            last_id=last_id,
            series_alias=SQL.identifier(series_alias),
        )

    def copy_many2one(field_: Field) -> SQL:
        comodel = typing.cast("Model", model.env[field_.comodel_name])
        if comodel in populated:
            comodel_max_id = populated[comodel]
            return SQL(
                "%(table_alias)s.%(field_name)s + %(comodel_max_id)s * (MOD(%(series_alias)s - 1, %(factor)s) + 1)",
                table_alias=SQL.identifier(table_alias),
                field_name=SQL.identifier(field_.name),
                comodel_max_id=comodel_max_id,
                series_alias=SQL.identifier(series_alias),
                factor=factors[comodel],
            )
        return copy(field_)

    if field.name == "id":
        return copy_id()
    match field.type:
        case "one2many" | "many2many":
            return None
        case "many2one":
            return copy_many2one(field)
        case "many2one_reference":
            return copy(field)
        case "binary":
            return None if field.attachment else copy(field)
        case _:
            return copy(field)


def populate_model(
    model: Model,
    populated: dict[Any, int],
    factors: dict[Any, int],
    separator_code: int,
    id_offset: int | None = None,
) -> None:
    def update_sequence(model_: Model) -> None:
        model_.env.execute_query(
            SQL(
                "SELECT SETVAL(PG_GET_SERIAL_SEQUENCE(QUOTE_IDENT(%(table)s), 'id'), "
                "MAX(id), TRUE) FROM %(id_table)s",
                table=_id_table(model_),
                id_table=SQL.identifier(_id_table(model_)),
            )
        )

    def has_column(field_: Field) -> bool:
        return field_.is_column

    assert model not in populated, (
        f"We do not populate a model ({model}) that has already been populated."
    )
    _logger.info("Populating model %s %s times...", model._name, factors[model])
    dest_fields = []
    src_fields = []
    update_fields = []
    table_alias = "t"
    series_alias = "s"
    unique_columns = unique_indexed_columns(model)
    for _, field in sorted(model._fields.items(), key=lambda pair: pair[0] != "id"):
        if has_column(field):
            if is_field_variation_required(
                model, field, unique_columns
            ) and field.type in (
                "char",
                "text",
            ):
                update_fields.append(field)
            if src := populate_field(
                model,
                field,
                populated,
                factors,
                table_alias,
                series_alias,
                unique_columns,
                id_offset,
            ):
                dest_fields.append(SQL.identifier(field.name))
                src_fields.append(src)
    _debug.pipeline(
        "populate.model_plan",
        model=model._name,
        factor=factors[model],
        columns=len(dest_fields),
        varied=[field.name for field in update_fields],
        unique_columns=len(unique_columns),
    )
    if update_fields:
        _logger.warning(
            "Renaming existing %s records to keep varied fields unique (%s): "
            "populate modifies original rows, not only the copies.",
            model._name,
            ", ".join(field.name for field in update_fields),
        )
        query = SQL(
            "UPDATE ONLY %(table)s SET (%(src_columns)s) = ROW(%(dest_columns)s)",
            table=SQL.identifier(model._table),
            src_columns=SQL(", ").join(
                SQL.identifier(field.name) for field in update_fields
            ),
            dest_columns=SQL(", ").join(
                get_field_variation_char(field, postfix=SQL("CHR(%s)", separator_code))
                for field in update_fields
            ),
        )
        model.env.cr.execute(query)
    query = SQL(
        """
        INSERT INTO %(table)s (%(dest_columns)s)
        SELECT %(src_columns)s FROM ONLY %(table)s %(table_alias)s,
        GENERATE_SERIES(1, %(factor)s) %(series_alias)s
    """,
        table=SQL.identifier(model._table),
        factor=factors[model],
        dest_columns=SQL(", ").join(dest_fields),
        src_columns=SQL(", ").join(src_fields),
        table_alias=SQL.identifier(table_alias),
        series_alias=SQL.identifier(series_alias),
    )
    with _debug.perf(
        "populate.model_insert",
        cr=model.env.cr,
        model=model._name,
        factor=factors[model],
        last_id=populated[model],
    ):
        model.env.cr.execute(query)
    if populated[model]:
        update_sequence(model)


class Many2oneFieldWrapper(Many2one):
    def __init__(self, model: Any, field_name: str, comodel_name: str) -> None:
        super().__init__(comodel_name)
        self._setup_attrs__(model, field_name)


class Many2manyModelWrapper:
    _table_inheritance_root = ""

    def __init__(self, env: Environment, field: Field) -> None:
        self._name = field.relation
        self._table = field.relation
        self._inherits: dict[str, str] = {}
        self.env = env
        self._rec_name = None
        self._rec_names_search: list[str] = []
        column1 = field.column1 or field.base_field.column1
        column2 = field.column2 or field.base_field.column2
        self._fields = {
            column1: Many2oneFieldWrapper(self, column1, field.model_name),
            column2: Many2oneFieldWrapper(self, column2, field.comodel_name or ""),
        }

    def __repr__(self) -> str:
        return f"<Many2manyModelWrapper({self._name!r})>"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Many2manyModelWrapper) and self._name == other._name

    def __hash__(self) -> int:
        return hash(self._name)


def infer_many2many_model(
    env: Environment, field: Field
) -> Model | Many2manyModelWrapper:
    for model_name, model_class in env.registry.items():
        if model_class._table == field.relation:
            return typing.cast("Model", env[model_name])
    return Many2manyModelWrapper(env, field)


def populate_models(model_factors: dict[Any, int], separator_code: int) -> None:

    def has_records(model_: Model, only: bool = False) -> bool:
        query = SQL(
            "SELECT EXISTS (SELECT 1 FROM %s%s)",
            SQL("ONLY ") if only else SQL(),
            SQL.identifier(model_._table),
        )
        return model_.env.execute_query(query)[0][0]

    populated: dict[Model, int] = defaultdict(int)
    ctx: PopulateContext = PopulateContext()

    def process(model_: Model) -> None:
        if model_ in populated:
            return
        members = [
            member for member in _tree_members(model_) if member not in populated
        ]
        if not has_records(model_):
            _debug.logic("populate.model_empty", model=model_._name)
            for member in members:
                populated[member] = 0
            return

        for member in members:
            model_factors.setdefault(member, model_factors[model_])
            for model_name in member._inherits:
                delegated = typing.cast("Model", member.env[model_name])
                model_factors.setdefault(delegated, model_factors[member])
                process(delegated)

        # The tables of an inheritance tree share the root's id sequence: their
        # copies take one offset past the whole tree, or they collide.
        id_offset = get_last_id(model_) if model_._table_inheritance_root else None
        _debug.logic(
            "populate.members",
            model=model_._name,
            tables=[member._table for member in members],
            id_offset=id_offset,
        )
        for member in members:
            if member in populated:
                continue
            if len(members) > 1 and not has_records(member, only=True):
                populated[member] = id_offset or 0
                continue
            with _debug.perf(
                "populate.model",
                cr=member.env.cr,
                model=member._name,
                factor=model_factors[member],
            ):
                with ctx.ignore_fkey_constraints(member), ctx.ignore_indexes(member):
                    populate_model(
                        member, populated, model_factors, separator_code, id_offset
                    )

        for member in members:
            for field in member._fields.values():
                if field.store and field.copy:
                    match field.type:
                        case "one2many":
                            comodel = typing.cast(
                                "Model", member.env[field.comodel_name]
                            )
                            if comodel != member:
                                model_factors.setdefault(comodel, model_factors[member])
                                process(comodel)
                        case "many2many":
                            m2m_model = typing.cast(
                                "Model", infer_many2many_model(member.env, field)
                            )
                            model_factors.setdefault(m2m_model, model_factors[member])
                            process(m2m_model)

    _debug.pipeline(
        "populate.start",
        models=[model._name for model in model_factors],
        separator=separator_code,
    )
    for model in list(model_factors):
        process(model)
    _debug.lifecycle(
        "populate.done",
        models=len(populated),
        populated=sum(1 for last_id in populated.values() if last_id),
    )
