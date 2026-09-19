import typing
from collections import defaultdict
from collections.abc import Iterable, Iterator, Reversible
from operator import attrgetter
from typing import override

from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import pg_varchar
from odoo.tools import OrderedSet, unique

from .._recordset import is_recordset
from .base import Field
from .numeric import Integer
from .selection import Selection

if typing.TYPE_CHECKING:
    from .._typing import ModelLike
    from ..models import BaseModel
    from ..primitives import IdType
    from .relational._base import _RelationalMulti

REFERENCE_VERIFIED_CACHE_KEY = "reference.verified_pairs"

_debug = DebugLog(__name__)


class Reference(Selection["BaseModel | None"]):
    type = "reference"
    cache_is_record_value = False
    cache_is_orderable = False
    cache_is_read_value = False

    _column_type = ("varchar", pg_varchar())

    if not typing.TYPE_CHECKING:
        __get__ = Field.__get__

    @override
    def convert_to_column(
        self,
        value: typing.Any,
        record: ModelLike,
        values: dict[str, typing.Any] | None = None,
        validate: bool = True,
    ) -> typing.Any:
        if is_recordset(value):
            value = self.convert_to_cache(value, record, validate)
        return Field.convert_to_column(self, value, record, values, validate)

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> str | None:
        if is_recordset(value):
            if value and not isinstance(value.id, int):
                # the cache holds "model,id" and the read parses the id back;
                # a NewId has no such form, and the read would fail far from here
                raise ValueError(
                    f"{self} cannot reference {value}: save the record first"
                )
            if not validate:
                return f"{value._name},{value.id}" if value else None
            if value._name in self.get_values(record.env) and len(value) <= 1:
                if not value:
                    return None
                res_id = value.id
                if isinstance(res_id, int):
                    memo = self._get_verified_pairs(record.env)
                    if (
                        value._name,
                        res_id,
                    ) not in memo and not self._reference_exists(
                        record, value._name, res_id, memo
                    ):
                        _debug.logic(
                            "field.reference.dangling_dropped",
                            model=self.model_name,
                            field=self.name,
                            res_model=value._name,
                            res_id=res_id,
                        )
                        return None
                return f"{value._name},{res_id}"
        elif isinstance(value, str):
            res_model, sep, res_id = value.partition(",")
            if sep and res_model:
                try:
                    res_id_int = int(res_id)
                except ValueError:
                    res_id_int = None
                if res_id_int is not None:
                    if not validate:
                        return value
                    memo = self._get_verified_pairs(record.env)
                    if (res_model, res_id_int) in memo:
                        return value
                    if res_model in self.get_values(record.env):
                        if self._reference_exists(record, res_model, res_id_int, memo):
                            return value
                        _debug.logic(
                            "field.reference.dangling_dropped",
                            model=self.model_name,
                            field=self.name,
                            res_model=res_model,
                            res_id=res_id_int,
                        )
                        return None
        elif not value:
            return None
        raise ValueError(f"Wrong value for {self}: {value!r}")

    def _get_verified_pairs(self, env) -> set[tuple[str, int]]:
        per_field = env.cr.cache.setdefault(REFERENCE_VERIFIED_CACHE_KEY, {})
        return per_field.setdefault((self.model_name, self.name), set())

    @staticmethod
    def discard_verified_models(env, model_names: typing.Iterable[str]) -> None:
        per_field = env.cr.cache.get(REFERENCE_VERIFIED_CACHE_KEY)
        if not per_field:
            return
        names = set(model_names)
        discarded = 0  # debuglog
        for pairs in per_field.values():
            stale = [pair for pair in pairs if pair[0] in names]
            pairs.difference_update(stale)
            discarded += len(stale)  # debuglog
        _debug.lifecycle(
            "field.reference.verified_pairs_discarded",
            models=sorted(names),
            pairs=discarded,
        )

    def _reference_exists(
        self,
        record: ModelLike,
        res_model: str,
        res_id: int,
        memo: set[tuple[str, int]],
    ) -> bool:
        env = record.env
        if (res_model, res_id) in memo:
            return True

        ids_per_model: dict[str, set[int]] = {res_model: {res_id}}

        prefetch_ids = [id_ for id_ in record._prefetch_ids if isinstance(id_, int)]
        if (
            len(record._ids) == 1
            and len(prefetch_ids) > 1
            and self.store
            and self.column_type
        ):
            # the siblings' stored pairs, verified in the same round
            stored = env.backend.columns.read(
                env[self.model_name], self.name, prefetch_ids
            )
            valid_models = None
            for sibling in set(stored.values()):
                if not sibling:
                    continue
                model, sep, id_str = sibling.partition(",")
                try:
                    sibling_id = int(id_str)
                except ValueError:
                    continue
                if not sep or not model or (model, sibling_id) in memo:
                    continue
                if valid_models is None:
                    valid_models = set(self.get_values(env))
                if model in valid_models and model in env.registry:
                    ids_per_model.setdefault(model, set()).add(sibling_id)

        with _debug.perf(
            "field.reference.verify",
            cr=env.cr,
            model=self.model_name,
            field=self.name,
            res_model=res_model,
            models=len(ids_per_model),
            candidates=sum(len(ids) for ids in ids_per_model.values()),
        ) as span:
            for model, ids in ids_per_model.items():
                existing = env[model].browse(ids).exists()
                memo.update((model, id_) for id_ in existing._ids)
            span.set(found=(res_model, res_id) in memo)

        return (res_model, res_id) in memo

    @override
    def convert_to_record(
        self, value: typing.Any, record: ModelLike
    ) -> BaseModel | None:
        if value:
            res_model, res_id = value.split(",")
            corecord = record.env[res_model].browse(int(res_id))
            # the siblings naming the same model fetch with it, as a
            # many2one's do
            corecord._prefetch_ids = PrefetchReference(record, self, res_model)
            return corecord
        return None

    @override
    def convert_to_read(
        self, value: typing.Any, record: ModelLike, use_display_name: bool = True
    ) -> str | typing.Literal[False]:
        return f"{value._name},{value.id}" if value else False

    @override
    def get_expression_getter(
        self, field_expr: str
    ) -> typing.Callable[[BaseModel], typing.Any]:
        if field_expr != self.name:
            return super().get_expression_getter(field_expr)
        read = self.__get__

        # the column holds "model,id" and every domain value takes that form;
        # the record the descriptor answers equals none of them
        def text(record: BaseModel) -> str | typing.Literal[False]:
            corecord = read(record)
            return f"{corecord._name},{corecord.id}" if corecord else False

        return text

    @override
    def convert_to_export(self, value: typing.Any, record: ModelLike) -> str:
        return value.display_name if value else ""

    @override
    def convert_to_display_name(
        self, value: typing.Any, record: ModelLike
    ) -> str | typing.Literal[False]:
        return value.display_name if value else False


class PrefetchReference(Reversible):
    __slots__ = ("field", "prefix", "record")

    def __init__(self, record: ModelLike, field: Reference, res_model: str) -> None:
        self.record = record
        self.field = field
        self.prefix = res_model + ","

    def _ids(self, record_ids: typing.Iterable[typing.Any]) -> Iterator[int]:
        field_cache = self.field._get_cache(self.record.env)
        prefix = self.prefix
        return unique(
            int(value[len(prefix) :])
            for id_ in record_ids
            if isinstance(value := field_cache.get(id_), str)
            and value.startswith(prefix)
        )

    def __iter__(self) -> Iterator[int]:
        return self._ids(self.record._prefetch_ids)

    def __reversed__(self) -> Iterator[int]:
        return self._ids(reversed(self.record._prefetch_ids))


class Many2oneReference(Integer):
    type = "many2one_reference"
    is_many2one_reference = True
    is_integer = False
    """Reset: Integer declares it, and this stores an id, not a number. The
    sites asking `is_integer` mean arithmetic -- `_increment_fields_skiplock`
    above all, which would happily increment a foreign key."""
    cache_is_record_value = False
    cache_is_orderable = False
    cache_is_read_value = False

    model_field = None
    aggregator = None

    _related_model_field = property(attrgetter("model_field"))

    _description_model_field = property(attrgetter("model_field"))

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> typing.Any:
        if is_recordset(value):
            value = value._ids[0] if value._ids else None
        return super().convert_to_cache(value, record, validate)

    def _update_inverse(self, records: BaseModel, value: BaseModel) -> None:
        self._update_cache(records, value.id or 0)

    @override
    def _update_inverses(self, updates: Iterable[tuple[BaseModel, typing.Any]]) -> None:
        updates = [(records, value) for records, value in updates if value]
        if not updates:
            return
        env = updates[0][0].env
        model_ids_per_update = [
            (records, value, self._get_record_ids_per_res_model(records))
            for records, value in updates
        ]
        for invf in env[self.model_name].pool.field_inverses[self]:
            invf = typing.cast("_RelationalMulti", invf)
            additions: dict[IdType, tuple[IdType, ...]] = {}
            for records, value, model_ids in model_ids_per_update:
                # A tree member's rows are referenced under the root's name.
                ids = model_ids.get(env[invf.model_name]._get_reference_model_name())
                if not ids:
                    continue
                corecord = env[invf.model_name].browse(value)
                recs = records.browse(ids).filtered_domain(
                    invf.get_comodel_domain(corecord)
                )
                if recs:
                    additions[corecord.id] = tuple(
                        unique(additions.get(corecord.id, ()) + recs._ids)
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
                invf._update_cache(
                    env[invf.model_name].browse((coid,)), ids1, keep_other_scopes=True
                )

    def _get_record_ids_per_res_model(
        self, records: BaseModel
    ) -> dict[str, OrderedSet]:
        model_field = self.model_field
        if model_field is None:
            raise TypeError(f"{self} declares no model_field to group its ids by")
        model_ids: defaultdict[str, OrderedSet] = defaultdict(OrderedSet)
        for record in records:
            model = record[model_field]
            if not model and record._fields[model_field].compute:
                record._fields[model_field].compute_value(record)
                model = record[model_field]
                if not model:
                    continue
            model_ids[model].add(record.id)
        return model_ids
