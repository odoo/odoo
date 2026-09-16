import typing
from collections.abc import (
    Iterable,
    Iterator,
    Reversible,
)
from typing import override

from odoo.exceptions import AccessError, MissingError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query, unique
from odoo.tools.misc import PENDING, SENTINEL, Sentinel

from ..._recordset import is_recordset
from ...domain import Domain
from ...domain.ast import DomainCondition, OptimizationLevel
from ...primitives import Command, IdType, NewId
from .. import _field_ddl as _ddl
from ._base import _is_cache_order_stable, _Relational, _RelationalMulti

if typing.TYPE_CHECKING:
    from ..._typing import ModelClass, ModelLike
    from ...models import BaseModel

    OnDelete = typing.Literal["cascade", "set null", "restrict"]

_debug = DebugLog(__name__)


def _optimize_comodel_id_lookup(condition: DomainCondition) -> Domain | None:
    operator = condition.operator
    if (
        operator not in ("any!", "not any!")
        or not isinstance(subdomain := condition.value, DomainCondition)
        or subdomain.field_expr != "id"
        or (suboperator := subdomain.operator)
        not in ("in", "not in", "any!", "not any!")
    ):
        return None
    val = subdomain.value
    domain: Domain
    match suboperator:
        case "in":
            domain = DomainCondition(condition.field_expr, "in", val - {False})
        case "not in":
            domain = DomainCondition(condition.field_expr, "not in", val | {False})
        case "any!":
            domain = DomainCondition(condition.field_expr, "any!", val)
        case "not any!":
            domain = DomainCondition(
                condition.field_expr, "!=", False
            ) & DomainCondition(condition.field_expr, "not any!", val)
    if operator == "not any!":
        domain = ~domain
    return domain


class Many2one(_Relational):
    type = "many2one"
    is_many2one = True
    _column_type = ("int4", "int4")

    ondelete: OnDelete | None = None
    delegate: bool = False

    @property
    def is_delegating(self) -> bool:
        return self.delegate

    @override
    def _optimize_condition(
        self, condition: DomainCondition, model: BaseModel, level: OptimizationLevel
    ) -> Domain:
        if level == OptimizationLevel.FULL:
            domain = _optimize_comodel_id_lookup(condition)
            if domain is not None:
                _debug.logic(
                    "field.many2one.id_lookup_flattened",
                    model=model._name,
                    field=condition.field_expr,
                    operator=condition.operator,
                )
                return domain
        return super()._optimize_condition(condition, model, level)

    def __init__(
        self,
        comodel_name: str | Sentinel = SENTINEL,
        string: str | Sentinel = SENTINEL,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(comodel_name=comodel_name, string=string, **kwargs)

    @override
    def _setup_attrs__(self, model_class: ModelClass, name: str) -> None:
        super()._setup_attrs__(model_class, name)
        if name in model_class._inherits.values():
            self.delegate = True
            self.bypass_search_access = True
            _debug.lifecycle(
                "field.many2one.delegate",
                model=model_class._name,
                field=name,
                comodel=self.comodel_name,
            )
        elif self.delegate:
            comodel_name = self.comodel_name or "comodel_name"
            raise TypeError(
                f"The delegate field {self} must be declared in the model class e.g.\n"
                f"_inherits = {{{comodel_name!r}: {name!r}}}"
            )

    @override
    def setup_nonrelated(self, model: BaseModel) -> None:
        super().setup_nonrelated(model)
        if not self.ondelete:
            comodel = model.env[self.comodel_name]
            if model.is_transient() and not comodel.is_transient():
                self.ondelete = "cascade" if self.required else "set null"
            else:
                self.ondelete = "restrict" if self.required else "set null"
            _debug.logic(
                "field.many2one.ondelete_defaulted",
                model=self.model_name,
                field=self.name,
                comodel=self.comodel_name,
                ondelete=self.ondelete,
                required=self.required,
                transient=model.is_transient(),
            )
        if self.ondelete == "set null" and self.required:
            raise ValueError(
                f"The m2o field {self.name} of model {model._name} is required but declares its ondelete policy "
                "as being 'set null'. Only 'restrict' and 'cascade' make sense."
            )
        if (
            self.ondelete == "restrict"
            and model.env[self.comodel_name]._is_registry_metadata
        ):
            raise ValueError(
                f"Field {self.name} of model {model._name} is defined as ondelete='restrict' "
                f"while having {self.comodel_name} as comodel, the 'restrict' mode is not "
                f"supported for this type of field as comodel."
            )

    @override
    def update_db(
        self, model: ModelLike, columns: dict[str, dict[str, typing.Any]]
    ) -> bool:
        comodel = model.env[self.comodel_name]
        if not model.is_transient() and comodel.is_transient():
            raise ValueError(
                f"Many2one {self} from Model to TransientModel is forbidden"
            )
        return super().update_db(model, columns)

    @override
    def update_db_column(self, model: ModelLike, column: dict[str, typing.Any]) -> None:
        super().update_db_column(model, column)
        model.pool.post_init(self.update_db_foreign_key, model, column)

    def update_db_foreign_key(
        self, model: BaseModel, column: dict[str, typing.Any]
    ) -> None:
        _ddl.update_db_foreign_key(self, model, column)

    @override
    def _update_inverse(self, records: BaseModel, value: BaseModel) -> None:
        self._update_cache(
            records, self.convert_to_cache(value, records, validate=False)
        )

    @override
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict | None = None,
        validate: bool = True,
    ) -> int | None:
        return value or None

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> int | NewId | None:
        id_: int | NewId | None
        if type(value) is int or type(value) is NewId:
            id_ = value
        elif is_recordset(value):
            if validate and (value._name != self.comodel_name or len(value) > 1):
                raise ValueError(f"Wrong value for {self}: {value!r}")
            id_ = value._ids[0] if value._ids else None
        elif isinstance(value, tuple):
            if validate:
                self._reject_command_tuple(value)
            id_ = (value[0] or None) if value else None
        elif isinstance(value, dict):
            comodel = record.env[self.comodel_name]
            origin = comodel.browse(value.get("id"))
            id_ = comodel.new(value, origin=origin).id
        elif validate and value:
            raise ValueError(f"Wrong value for {self}: {value!r}")
        else:
            id_ = None

        if self.delegate and record and not any(record._ids) and isinstance(id_, int):
            id_ = NewId(id_)

        return id_

    @override
    def convert_to_record(
        self, value: int | NewId | None, record: ModelLike
    ) -> BaseModel:
        rs = object.__new__(record.pool[self.comodel_name])
        rs.env = record.env
        rs._ids = () if value is None else (value,)
        rs._prefetch_ids = PrefetchMany2one(record, self)
        return rs

    def convert_to_record_multi(
        self, values: list[int | NewId | None], records: BaseModel
    ) -> BaseModel:
        rs = object.__new__(records.pool[self.comodel_name])
        rs.env = records.env
        rs._ids = tuple(unique(id_ for id_ in values if id_ is not None))
        rs._prefetch_ids = PrefetchMany2one(records, self)
        return rs

    @override
    def convert_to_read(
        self,
        value: BaseModel,
        record: ModelLike,
        use_display_name: bool = True,
    ) -> int | tuple[int, str] | typing.Literal[False]:
        return self.convert_to_read_multi([value], record, use_display_name)[0]

    def convert_to_read_multi(
        self,
        values: list[BaseModel],
        records: ModelLike,
        use_display_name: bool = True,
    ) -> list[typing.Any]:
        if not use_display_name:
            return [value.id for value in values]

        allowed_ids: set | None = None
        if target_ids := list(unique(value.id for value in values if value)):
            targets = records.env[self.comodel_name].browse(target_ids)
            try:
                allowed_ids = set(targets._filtered_display_name_access()._ids)
            except MissingError:
                allowed_ids = None
            if _debug.pipeline.enabled:
                _debug.pipeline(
                    "field.many2one.read_display_names",
                    model=self.model_name,
                    field=self.name,
                    comodel=self.comodel_name,
                    values=len(values),
                    targets=len(target_ids),
                    allowed=len(allowed_ids) if allowed_ids is not None else None,
                    per_record=allowed_ids is None,
                )

        result: list[typing.Any] = []
        for value in values:
            if not value:
                result.append(False)
                continue
            try:
                readable = (
                    value.id in allowed_ids
                    if allowed_ids is not None
                    else bool(value._filtered_display_name_access())
                )
                result.append(
                    (value.id, value.sudo().display_name) if readable else False
                )
            except MissingError:
                result.append(False)
        return result

    @override
    def convert_to_write(
        self, value: typing.Any, record: ModelLike
    ) -> int | NewId | typing.Literal[False]:
        if type(value) is int or type(value) is NewId:
            return value
        if not value:
            return False
        if is_recordset(value) and value._name == self.comodel_name:
            record_id = value.id
            return record_id if isinstance(record_id, (int, NewId)) else False
        if isinstance(value, tuple):
            self._reject_command_tuple(value)
            return value[0] if value else False
        if isinstance(value, dict):
            return record.env[self.comodel_name].new(value).id
        raise ValueError(f"Wrong value for {self}: {value!r}")

    def _reject_command_tuple(self, value: tuple) -> None:
        if len(value) == 3 and isinstance(value[0], int):
            if value[0] in Command._value2member_map_:
                raise ValueError(
                    f"Wrong value for {self}: x2many Command tuple "
                    f"{value!r} cannot be assigned to a many2one field"
                )

    @override
    def convert_to_export(self, value: BaseModel, record: ModelLike) -> str:
        return value.display_name or "" if value else ""

    @override
    def convert_to_display_name(
        self, value: BaseModel, record: ModelLike
    ) -> str | typing.Literal[False]:
        return value.display_name

    @override
    def mark_dirty(self, records: BaseModel, value: typing.Any) -> None:
        records.env.remove_to_compute(self, records)

        cache_value = self.convert_to_cache(value, records)

        if self.bypass_search_access and not records.env.su:
            _debug.logic(
                "field.many2one.write_target_access_checked",
                model=self.model_name,
                field=self.name,
                comodel=self.comodel_name,
                target=cache_value,
                uid=records.env.uid,
            )
            try:
                records.env[self.comodel_name].browse(cache_value).check_access("read")
            except AccessError as e:
                raise AccessError(
                    records.env._("Failed to write field %s", self) + "\n" + str(e)
                ) from e

        records = self._filter_not_equal(records, cache_value)
        if not records:
            return

        self._remove_inverses(records)

        self._update_cache(records, cache_value, dirty=True)

        self._update_inverses([(records, cache_value)])
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "field.many2one.dirty",
                model=self.model_name,
                field=self.name,
                records=len(records),
                target=cache_value,
                inverses=len(records.pool.field_inverses[self]),
            )

    def _remove_inverses(self, records: BaseModel) -> None:
        inverse_fields = records.pool.field_inverses[self]
        if not inverse_fields:
            return

        record_ids = set(records._ids)
        field_cache = self._get_cache(records.env)
        _pending = PENDING
        corecords = records.env[self.comodel_name].browse(
            coid if record_id else (coid and NewId(coid))
            for record_id in records._ids
            if (coid := field_cache.get(record_id)) is not None and coid is not _pending
        )

        for invf in inverse_fields:
            invf = typing.cast("_RelationalMulti", invf)
            inv_cache = invf._get_cache(corecords.env)
            for corecord in corecords:
                invf._sync_other_scopes(corecords.env, corecord.id, removed=record_ids)
                ids0 = inv_cache.get(corecord.id)
                if ids0 is not None:
                    ids1 = tuple(id_ for id_ in ids0 if id_ not in record_ids)
                    invf._update_cache(corecord, ids1, keep_other_scopes=True)

    def _resort_inverses(self, records: BaseModel) -> None:
        env = records.env
        field_cache = self._get_cache(env)
        corecord_ids = {
            coid
            for id_ in records._ids
            if (coid := field_cache.get(id_)) and isinstance(coid, int)
        }
        if not corecord_ids:
            return
        changed_ids = set(records._ids)
        for invf in records.pool.field_inverses[self]:
            if not invf.is_one2many:
                continue
            inv_cache = invf._get_cache(env)
            for coid in corecord_ids:
                ids0 = inv_cache.get(coid)
                if (
                    not isinstance(ids0, tuple)
                    or len(ids0) < 2
                    or changed_ids.isdisjoint(ids0)
                    or not all(isinstance(id_, int) for id_ in ids0)
                ):
                    continue
                ids1 = records.browse(ids0)._sorted_by_ids(records._order, False)
                if ids1 is not None and ids1 != ids0:
                    _debug.logic(
                        "field.many2one.inverse_resorted",
                        model=self.model_name,
                        field=self.name,
                        inverse=f"{invf.model_name}.{invf.name}",
                        corecord=coid,
                    )
                    invf._update_cache(env[invf.model_name].browse(coid), ids1)

    def _update_inverses(
        self, updates: Iterable[tuple[BaseModel, int | NewId | None]]
    ) -> None:
        updates = [(records, value) for records, value in updates if value is not None]
        if not updates:
            return
        env = updates[0][0].env
        model = env[self.model_name]
        for invf in model.pool.field_inverses[self]:
            invf = typing.cast("_RelationalMulti", invf)
            additions: dict[IdType, tuple[IdType, ...]] = {}
            for records, value in updates:
                corecord = self.convert_to_record(value, records)
                valid_records = records.filtered_domain(
                    invf.get_comodel_domain(corecord)
                )
                if valid_records:
                    additions[corecord.id] = tuple(
                        unique(additions.get(corecord.id, ()) + valid_records._ids)
                    )
            if not additions:
                continue
            invf._sync_added_to_other_scopes(env, additions)
            inv_cache = invf._get_cache(env)
            for coid, added in additions.items():
                ids0 = inv_cache.get(coid)
                if ids0 is None and coid:
                    continue
                ids1 = tuple(unique((ids0 or ()) + added))
                if coid and not _is_cache_order_stable(model, ids1):
                    # never invalidate here: the next read would fetch, and a
                    # fetch flushes the half-written transaction this call is
                    # part of
                    sorted_ids = model.browse(ids1)._sorted_by_ids(model._order, False)
                    if sorted_ids is not None:
                        ids1 = sorted_ids
                    if _debug.logic.enabled and sorted_ids is None:
                        _debug.logic(
                            "field.many2one.inverse_appended_unsorted",
                            model=self.model_name,
                            field=self.name,
                            inverse=f"{invf.model_name}.{invf.name}",
                            corecord=coid,
                        )
                invf._update_cache(
                    env[invf.model_name].browse((coid,)), ids1, keep_other_scopes=True
                )

    @override
    def to_sql(self, model: ModelLike, alias: str) -> SQL:
        sql_field = super().to_sql(model, alias)
        if self.company_dependent:
            comodel = model.env[self.comodel_name]
            _debug.logic(
                "field.many2one.company_dependent_exists_subselect",
                model=model._name,
                field=self.name,
                comodel=self.comodel_name,
                alias=alias,
            )
            sql_field = SQL(
                """(SELECT %(cotable_alias)s.id
                    FROM %(cotable)s AS %(cotable_alias)s
                    WHERE %(cotable_alias)s.id = %(ref)s)""",
                cotable=SQL.identifier(comodel._table),
                cotable_alias=SQL.identifier(
                    Query.get_table_alias(comodel._table, "exists")
                ),
                ref=sql_field,
            )
        return sql_field

    @override
    def condition_to_sql(
        self,
        field_expr: str,
        operator: str,
        value: typing.Any,
        model: BaseModel,
        alias: str,
        query: Query,
    ) -> SQL:
        if (
            operator not in ("any", "not any", "any!", "not any!")
            or field_expr != self.name
        ):
            return super().condition_to_sql(
                field_expr, operator, value, model, alias, query
            )

        comodel = model.env[self.comodel_name]
        sql_field = model._field_to_sql(alias, field_expr, query)
        can_be_null = self not in model.env.registry.not_null_fields
        bypass_access = operator in ("any!", "not any!") or self.bypass_search_access
        positive = operator in ("any", "any!")

        left_join = bypass_access and isinstance(value, Domain)
        if left_join and not positive:
            left_join = sum(
                (-1 if cond.operator in Domain.NEGATIVE_OPERATORS else 1)
                for cond in value.iter_conditions()
            ) < 0 or any(
                cond.field_expr == "id"
                and cond.operator not in Domain.NEGATIVE_OPERATORS
                for cond in value.iter_conditions()
            )

        _debug.logic(
            "field.many2one.any_strategy",
            model=model._name,
            field=self.name,
            operator=operator,
            strategy="left_join" if left_join else "subselect",
            bypass_access=bypass_access,
        )
        if left_join:
            comodel, coalias = self.join(model, alias, query)
            if not positive:
                value = (~value).optimize_full(comodel)
            sql = value._to_sql(comodel, coalias, query)
            if self.company_dependent:
                sql = self._condition_to_sql_company(
                    sql, field_expr, operator, value, model, alias, query
                )
            if can_be_null:
                if positive:
                    sql = SQL("(%s IS NOT NULL AND %s)", sql_field, sql)
                else:
                    sql = SQL("(%s IS NULL OR %s)", sql_field, sql)
            return sql

        if isinstance(value, Domain):
            value = comodel._search(
                value, active_test=False, bypass_access=bypass_access
            )
        if isinstance(value, Query):
            subselect = value.subselect()
        elif isinstance(value, SQL):
            subselect = SQL("(%s)", value)
        else:
            raise TypeError(
                f"condition_to_sql() 'any' operator accepts Domain, SQL or Query, got {value}"
            )
        sql = SQL(
            "%s%s%s",
            sql_field,
            SQL(" IN ") if positive else SQL(" NOT IN "),
            subselect,
        )
        if can_be_null and not positive:
            sql = SQL("(%s IS NULL OR %s)", sql_field, sql)
        if self.company_dependent:
            sql = self._condition_to_sql_company(
                sql, field_expr, operator, value, model, alias, query
            )
        return sql

    def join(self, model: ModelLike, alias: str, query: Query) -> tuple[BaseModel, str]:
        comodel = model.env[self.comodel_name]
        coalias = query.get_table_alias(alias, self.name)
        _debug.pipeline(
            "field.many2one.join",
            model=model._name,
            field=self.name,
            comodel=self.comodel_name,
            alias=alias,
            coalias=coalias,
        )
        query.add_join(
            "LEFT JOIN",
            coalias,
            comodel._table,
            SQL(
                "%s = %s",
                model._field_to_sql(alias, self.name, query),
                SQL.identifier(coalias, "id"),
            ),
        )
        return (comodel, coalias)


class PrefetchMany2one(Reversible):
    __slots__ = ("field", "record")

    def __init__(self, record: ModelLike, field: Many2one) -> None:
        self.record = record
        self.field = field

    def __iter__(self) -> Iterator[int | NewId]:
        field_cache = self.field._get_cache(self.record.env)
        _pending = PENDING
        return unique(
            coid
            for id_ in self.record._prefetch_ids
            if (coid := field_cache.get(id_)) is not None and coid is not _pending
        )

    def __reversed__(self) -> Iterator[int | NewId]:
        field_cache = self.field._get_cache(self.record.env)
        _pending = PENDING
        return unique(
            coid
            for id_ in reversed(self.record._prefetch_ids)
            if (coid := field_cache.get(id_)) is not None and coid is not _pending
        )
