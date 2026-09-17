import itertools
import typing
from collections.abc import (
    Callable,
    Collection,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Reversible,
    Sequence,
)
from operator import attrgetter
from typing import override

from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, OrderedSet, Query, partition, unique
from odoo.tools.misc import PENDING, SENTINEL, unquote

from ..._recordset import is_recordset, is_search_overridden
from ...constants import READ_GROUP_NUMBER_GRANULARITY
from ...domain import Domain
from ...domain.ast import DomainCondition, OptimizationLevel
from ...domain.constants import (
    NEGATIVE_CONDITION_OPERATORS,
    SUBDOMAIN_OPERATORS,
)
from ...primitives import COLLECTION_TYPES, PREFETCH_MAX, Command, IdType, NewId
from .._field_cache_miss import missing_record_error
from ..base import Field, _logger
from ._commands import CommandDelta

_debug = DebugLog(__name__)

_COMODEL_WRITING_COMMANDS = frozenset({Command.CREATE, Command.UPDATE, Command.DELETE})


def _strip_granularity_suffix(field_expr: str) -> str:
    prefix, _sep, last = field_expr.rpartition(".")
    if prefix and last in READ_GROUP_NUMBER_GRANULARITY:
        return prefix
    return field_expr


def _iter_domain_depend_paths(domain: Domain) -> Iterator[str]:
    for condition in domain.iter_conditions():
        yield _strip_granularity_suffix(condition.field_expr)
        value = condition.value
        if isinstance(value, Domain):
            subdomain = value
        elif condition.operator in SUBDOMAIN_OPERATORS and isinstance(
            value, (list, tuple)
        ):
            subdomain = Domain(value, internal=True)
        else:
            continue
        for sub_path in _iter_domain_depend_paths(subdomain):
            yield f"{condition.field_expr}.{sub_path}"


if typing.TYPE_CHECKING:
    from odoo.tools.misc import Collector

    from ..._typing import (
        CommandValue,
        DomainType,
        Environment,
        ModelLike,
        Registry,
    )
    from ...models import BaseModel


class _Relational(Field["BaseModel"]):
    relational: typing.Literal[True] = True
    comodel_name: str
    domain: DomainType = []
    bypass_search_access: bool = False
    check_company: bool = False

    @override
    def _optimize_condition(
        self, condition: DomainCondition, model: BaseModel, level: OptimizationLevel
    ) -> Domain:
        if level != OptimizationLevel.BASIC:
            return condition
        operator = condition.operator
        value = condition.value
        positive_operator = NEGATIVE_CONDITION_OPERATORS.get(operator, operator)
        any_operator = "any" if positive_operator == operator else "not any"
        if operator.endswith("like"):
            _debug.logic(
                "field.relational.display_name_rewrite",
                model=model._name,
                field=condition.field_expr,
                operator=operator,
                kind="like",
            )
            return DomainCondition(
                condition.field_expr,
                any_operator,
                DomainCondition("display_name", positive_operator, value),
            )
        if operator[0] in ("<", ">") and (
            isinstance(value, (str, bool, *COLLECTION_TYPES)) or is_recordset(value)
        ):
            raise condition._prepare_condition_error(
                "Inequality on a relational field is only supported against a "
                "single record id",
                error=TypeError,
            )
        if positive_operator != "in" or not isinstance(value, COLLECTION_TYPES):
            return condition
        if not any(isinstance(v, str) for v in value):
            return condition
        str_values, other_values = partition(lambda v: isinstance(v, str), value)
        _debug.logic(
            "field.relational.display_name_rewrite",
            model=model._name,
            field=condition.field_expr,
            operator=operator,
            kind="in",
            names=len(str_values),
            ids=len(other_values),
        )
        domain: Domain = DomainCondition(
            condition.field_expr,
            any_operator,
            DomainCondition("display_name", positive_operator, str_values),
        )
        if other_values:
            if positive_operator == operator:
                domain |= DomainCondition(condition.field_expr, operator, other_values)
            else:
                domain &= DomainCondition(condition.field_expr, operator, other_values)
        return domain

    @override
    def _get_not_singleton(
        self, records: BaseModel, owner: typing.Any = None
    ) -> BaseModel:
        if not records._ids:
            return super()._get_not_singleton(records, owner)

        env = records.env
        if self.is_stored_computed and env.core.has_pending_field(self):
            self.recompute(records)

        field_cache = self._get_cache(env)

        check_pending = self.is_stored_computed
        vals: list[typing.Any] = []
        _append = vals.append
        for record_id in records._ids:
            try:
                value = field_cache[record_id]
            except KeyError:
                pass
            else:
                if not (check_pending and value is PENDING):
                    _append(value)
                    continue
                field_cache.pop(record_id, None)
                record = records.browse(record_id)
                if env.is_protected(self, record):
                    value = self.convert_to_cache(False, record, validate=False)
                    self._update_cache(record, value)
                    _append(value)
                    continue
            if self.store and record_id and len(vals) < len(records) - PREFETCH_MAX:
                remaining = records[len(vals) :]
                _debug.logic(
                    "field.relational.multi_get_fetch",
                    model=self.model_name,
                    field=self.name,
                    records=len(records),
                    cached=len(vals),
                    remaining=len(remaining),
                )
                remaining.fetch([self.name])
                field_cache = self._get_cache(env)
                if record_id not in field_cache:
                    raise missing_record_error(env, record_id) from None
            else:
                remaining = object.__new__(records.__class__)
                remaining.env = env
                remaining._ids = (record_id,)
                remaining._prefetch_ids = records._prefetch_ids
                super().__get__(remaining, owner)
                field_cache = self._get_cache(env)
            _append(field_cache[record_id])

        return self.convert_to_record_multi(vals, records)

    def _update_inverse(self, records: BaseModel, value: BaseModel) -> None:
        raise NotImplementedError

    def convert_to_record_multi(self, values: list, records: BaseModel) -> BaseModel:
        raise NotImplementedError

    @override
    def setup_nonrelated(self, model: BaseModel) -> None:
        super().setup_nonrelated(model)
        assert self.comodel_name in model.pool, (
            f"Field {self} with unknown comodel_name {self.comodel_name or '???'!r}"
        )

    def setup_inverses(
        self, registry: Registry, inverses: Collector[Field, Field]
    ) -> None:
        pass

    def get_comodel_domain(self, model: ModelLike) -> Domain:
        domain = self.domain
        if callable(domain):
            domain = domain(model)
        if not domain or isinstance(domain, str):
            return Domain.TRUE
        return Domain(domain)

    @property
    def _related_domain(self) -> DomainType | None:
        def validated(domain):
            if isinstance(domain, str) and not self.inherited:
                return None
            return domain

        if callable(self.domain):
            return lambda recs: validated(self.domain(recs.env[self.model_name]))
        else:
            return validated(self.domain)

    _related_context = property(attrgetter("context"))

    _description_relation = property(attrgetter("comodel_name"))
    _description_context = property(attrgetter("context"))

    @override
    def _dynamic_description_attrs(self, env: Environment) -> frozenset[str]:
        dynamic = super()._dynamic_description_attrs(env)
        if callable(self.domain):
            return dynamic | {"domain"}
        return dynamic

    def _description_domain(self, env: Environment) -> str | list:
        domain = self._internal_description_domain_raw(env)
        if self.check_company:
            field_to_check = None
            if self.company_dependent:
                cids = "[allowed_company_ids[0]]"
            elif self.model_name == "res.company":
                cids = "[id]"
            elif "company_id" in env[self.model_name]:
                cids = "[company_id]"
                field_to_check = "company_id"
            elif "company_ids" in env[self.model_name]:
                cids = "company_ids"
                field_to_check = "company_ids"
            else:
                _logger.warning(
                    env._(
                        "Couldn't generate a company-dependent domain for field %s. "
                        "The model doesn't have a 'company_id' or 'company_ids' field, and isn't company-dependent either.",
                        self.model_name + "." + self.name,
                    )
                )
                return domain
            company_domain = env[self.comodel_name]._check_company_domain(
                companies=unquote(cids)
            )
            if not field_to_check:
                return f"{company_domain} + {domain or []}"
            else:
                no_company_domain = env[self.comodel_name]._check_company_domain(
                    companies=""
                )
                return f"({field_to_check} and {company_domain} or {no_company_domain}) + ({domain or []})"
        return domain

    def _description_allow_hierarchy_operators(self, env: Environment) -> bool:
        comodel = env[self.comodel_name]
        return comodel._parent_name in comodel._fields

    def _internal_description_domain_raw(self, env: Environment) -> str | list:
        domain = self.domain
        if callable(domain):
            domain = domain(env[self.model_name])
        if isinstance(domain, Domain):
            return list(domain) or []
        return domain or []

    @override
    def filter_function(
        self,
        records: BaseModel,
        field_expr: str,
        operator: str,
        value: typing.Any,
    ) -> Callable[[BaseModel], bool]:
        getter = self.get_expression_getter(field_expr)

        _debug.logic(
            "field.relational.filter_function",
            model=self.model_name,
            field_expr=field_expr,
            operator=operator,
            records=len(records),
            sudo=(self.bypass_search_access or operator == "any!")
            and not records.env.su,
        )
        if (self.bypass_search_access or operator == "any!") and not records.env.su:
            expr_getter = getter
            sudo_env = records.sudo().with_context(filter_function_reset_sudo=True).env

            def getter(rec):
                return expr_getter(rec.with_env(sudo_env))

        corecords = getter(records)
        if operator in ("any", "any!"):
            assert isinstance(value, Domain)
            if operator == "any" and records.env.context.get(
                "filter_function_reset_sudo"
            ):
                corecords = corecords.sudo(False)._filtered_access("read")
            corecords = corecords.filtered_domain(value)
        elif operator == "in" and isinstance(value, COLLECTION_TYPES):
            value = set(value)
            if False in value:
                if not corecords:
                    return lambda _: True
                if len(value) > 1:
                    value.discard(False)
                    filter_values = self.filter_function(
                        records, field_expr, "in", value
                    )
                    return lambda rec: not getter(rec) or filter_values(rec)
                return lambda rec: not getter(rec)
            corecords = corecords.filtered_domain(Domain("id", "in", value))
        else:
            corecords = corecords.filtered_domain(Domain("id", operator, value))

        if not corecords:
            return lambda _: False

        ids = set(corecords._ids)
        return lambda rec: not ids.isdisjoint(getter(rec)._ids)


PENDING_SCOPE_KEY = ("__pending__",)


def _is_cache_order_stable(records: BaseModel, ids: tuple) -> bool:
    # A new record cannot be read back from the database, so its id stays in the cache.
    if not all(isinstance(id_, int) for id_ in ids):
        return True
    return records._order.replace(" ", "").lower() in ("id", "idasc") and list(
        ids
    ) == sorted(ids)


class _ScopedSlot(MutableMapping):
    __slots__ = ("pending", "scoped")

    def __init__(self, scoped: dict, pending: dict) -> None:
        self.scoped = scoped
        self.pending = pending

    def _pick(self, key: typing.Any) -> dict:
        return self.scoped if isinstance(key, int) else self.pending

    def __getitem__(self, key: typing.Any) -> typing.Any:
        return self._pick(key)[key]

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        self._pick(key)[key] = value

    def __delitem__(self, key: typing.Any) -> None:
        del self._pick(key)[key]

    def __contains__(self, key: object) -> bool:
        return key in self._pick(key)

    def __iter__(self) -> Iterator:
        yield from self.scoped
        yield from self.pending

    def __len__(self) -> int:
        return len(self.scoped) + len(self.pending)

    def __bool__(self) -> bool:
        return bool(self.scoped) or bool(self.pending)

    def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        return self._pick(key).get(key, default)

    def pop(self, key: typing.Any, *default: typing.Any) -> typing.Any:
        return self._pick(key).pop(key, *default)

    def setdefault(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        return self._pick(key).setdefault(key, default)

    def clear(self) -> None:
        self.scoped.clear()
        self.pending.clear()


class _RelationalMulti(_Relational):
    write_sequence = 20
    is_x2many = True

    @override
    def _optimize_condition(
        self, condition: DomainCondition, model: BaseModel, level: OptimizationLevel
    ) -> Domain:
        domain = super()._optimize_condition(condition, model, level)
        if domain != condition:
            return domain
        if level == OptimizationLevel.BASIC and condition.operator in (
            ">",
            "<",
            ">=",
            "<=",
        ):
            raise condition._prepare_condition_error(
                "Cannot use an ordering comparison on the to-many field %r; "
                "use 'any' with a sub-domain",
                condition.field_expr,
                error=TypeError,
            )
        return condition

    @override
    def _update_inverse(self, records: BaseModel, value: BaseModel) -> None:
        new_id = value.id
        assert not new_id, "Field._update_inverse can only be called with a new id"
        field_cache = self._get_cache(records.env)
        for record_id in records._ids:
            assert not record_id, (
                "Field._update_inverse can only be called with new records"
            )
            cache_value = field_cache.get(record_id, SENTINEL)
            if cache_value is SENTINEL:
                records.env.core.add_patch(self, record_id, new_id)
            else:
                field_cache[record_id] = tuple(unique(cache_value + (new_id,)))

    @override
    def _get_cache_impl(self, env: Environment) -> MutableMapping[IdType, typing.Any]:
        core = env.core
        return _ScopedSlot(
            core.get_context_data(self, env.get_cache_key(self)),
            core.get_context_data(self, PENDING_SCOPE_KEY),
        )

    @override
    def _peek_cache(self, env: Environment) -> Mapping[IdType, typing.Any] | None:
        core = env.core
        scoped = core.get_context_data_or_none(self, env.get_cache_key(self))
        pending = core.get_context_data_or_none(self, PENDING_SCOPE_KEY)
        if scoped is None and pending is None:
            return None
        return _ScopedSlot(scoped if scoped is not None else {}, pending or {})

    @override
    def _value_after_delegated_fetch(
        self, env: Environment, record_id: IdType
    ) -> typing.Any:
        if env.su or not isinstance(record_id, int):
            return SENTINEL
        sudo_slot = env.core.get_context_data_or_none(
            self, self._superuser_scope_key(env)
        )
        if sudo_slot is None:
            return SENTINEL
        value = sudo_slot.get(record_id, SENTINEL)
        if value is SENTINEL or value is PENDING:
            return SENTINEL
        self._get_cache(env)[record_id] = value
        _debug.logic(
            "field.x2many.delegated_fetch_served",
            model=self.model_name,
            field=self.name,
            record=record_id,
            uid=env.uid,
        )
        return value

    def _is_superuser_scope(self, env: Environment, key: tuple) -> bool:
        index = env._field_depends_context[self].index("access")
        return key[index] is True or key[index] is None

    def _reads_as_superuser(self, env: Environment) -> bool:
        # a user's read equals the superuser's only when nothing narrows it:
        # a static field domain, a comodel whose _search is not overridden,
        # model access, and no read rule for the user on the comodel
        comodel = env[self.comodel_name]
        if callable(self.domain) or is_search_overridden(type(comodel)):
            return False
        policy = env.registry.access_policy
        try:
            return policy.model_allowed(env, self.comodel_name, "read") and (
                not policy.record_domain(env, self.comodel_name, "read")
            )
        except NotImplementedError:
            return False

    def _scope_env(self, env: Environment, key: tuple) -> Environment:
        index = env._field_depends_context[self].index("access")
        uid, company_ids = key[index]
        context = dict(env.context)
        if company_ids:
            context["allowed_company_ids"] = list(company_ids)
        else:
            context.pop("allowed_company_ids", None)
        return env(user=uid, context=context, su=False)

    def _scope_reads_through(
        self, env: Environment, key: tuple, fnames: Collection[str]
    ) -> bool:
        # a user's search applies the user's read rules on the comodel; a
        # write to a field a rule tests can move a record in or out of view.
        # A comodel whose _search is overridden narrows by code: it declares
        # the fields that code reads, or every write may have moved a record
        comodel_cls = type(env[self.comodel_name])
        if is_search_overridden(comodel_cls):
            visibility = comodel_cls._search_visibility_fields
            if visibility is None or not set(visibility).isdisjoint(fnames):
                return True
        try:
            domain = env.registry.access_policy.record_domain(
                self._scope_env(env, key), self.comodel_name, "read"
            )
        except NotImplementedError:
            # an environment without an access policy declares no rule
            return False
        except AccessError:
            # the scope names a company its user no longer holds: its rules can
            # no longer be read, and forgetting what it held is always safe
            _debug.logic(
                "field.x2many.scope_unreadable_evicted",
                model=self.model_name,
                field=self.name,
                uid=key[env._field_depends_context[self].index("access")][0],
            )
            return True
        return any(
            condition.field_expr.split(".", 1)[0] in fnames
            for condition in domain.iter_conditions()
        )

    def _evict_user_scopes_reading_through(
        self, env: Environment, fnames: Collection[str]
    ) -> None:
        # after a write of `fnames` on comodel rows: every user scope whose
        # read rule tests one of them forgets what it held, and its next
        # read searches; the superuser reads through no rule
        verdicts: dict[tuple, bool] = {}
        evicted = 0
        for key, slot in list(env.core.iter_context_caches(self)):
            if (
                key == PENDING_SCOPE_KEY
                or not slot
                or self._is_superuser_scope(env, key)
            ):
                continue
            if key not in verdicts:
                verdicts[key] = self._scope_reads_through(env, key, fnames)
            if verdicts[key]:
                evicted += len(slot)
                slot.clear()
        if evicted and _debug.logic.enabled:
            _debug.logic(
                "field.x2many.scope_evict_rule_field_written",
                model=self.model_name,
                field=self.name,
                comodel=self.comodel_name,
                fields=sorted(fnames),
                evicted=evicted,
            )

    def _superuser_scope_key(self, env: Environment) -> tuple:
        own = env.get_cache_key(self)
        index = env._field_depends_context[self].index("access")
        return (*own[:index], True, *own[index + 1 :])

    def _mirror_to_other_scopes(
        self, env: Environment, ids: Collection[IdType], cache_value: typing.Any
    ) -> None:
        own = env.get_cache_key(self)
        stored_ids = [id_ for id_ in ids if isinstance(id_, int)]
        mirrored = 0
        for key, slot in list(env.core.iter_context_caches(self)):
            if key in (own, PENDING_SCOPE_KEY):
                continue
            for id_ in stored_ids:
                if id_ in slot:
                    slot[id_] = cache_value
                    mirrored += 1
        if _debug.logic.enabled and mirrored:
            _debug.logic(
                "field.x2many.scope_mirror_pending",
                model=self.model_name,
                field=self.name,
                records=len(stored_ids),
                mirrored=mirrored,
                writer_su=env.su,
            )

    def _mirror_to_superuser_scope(
        self, env: Environment, ids: Collection[IdType], cache_value: typing.Any
    ) -> None:
        if env.su:
            return
        slot = env.core.get_context_data(self, self._superuser_scope_key(env))
        for id_ in ids:
            if isinstance(id_, int):
                slot[id_] = cache_value

    def _sync_other_scopes(
        self,
        env: Environment,
        record_id: IdType,
        added: Collection[IdType] = (),
        removed: Collection[IdType] = (),
    ) -> None:
        if not isinstance(record_id, int):
            return
        if added:
            self._sync_added_to_other_scopes(env, {record_id: tuple(added)})
        if not removed:
            return
        own = env.get_cache_key(self)
        synced = 0
        for key, slot in list(env.core.iter_context_caches(self)):
            if key in (own, PENDING_SCOPE_KEY) or record_id not in slot:
                continue
            ids = slot[record_id]
            if ids is PENDING:
                continue
            slot[record_id] = tuple(id_ for id_ in ids if id_ not in removed)
            synced += 1
        if synced and _debug.logic.enabled:
            _debug.logic(
                "field.x2many.scope_sync",
                model=self.model_name,
                field=self.name,
                record=record_id,
                added=0,
                removed=len(removed),
                synced=synced,
                evicted=0,
            )

    def _sync_added_to_other_scopes(
        self, env: Environment, additions: Mapping[IdType, tuple[IdType, ...]]
    ) -> None:
        # the superuser's slot takes every addition, it reads everything; a
        # user's slot is evicted rather than judged: judging costs the
        # comodel's read check now, evicting costs a search only if that user
        # reads the record again, and a direct x2many write evicts the same way
        additions = {
            id_: added
            for id_, added in additions.items()
            if isinstance(id_, int) and added
        }
        if not additions:
            return
        own = env.get_cache_key(self)
        comodel = env[self.comodel_name]
        synced = evicted = 0
        for key, slot in list(env.core.iter_context_caches(self)):
            if key in (own, PENDING_SCOPE_KEY):
                continue
            held = [
                id_ for id_ in additions if id_ in slot and slot[id_] is not PENDING
            ]
            if not held:
                continue
            if not self._is_superuser_scope(env, key):
                for id_ in held:
                    del slot[id_]
                evicted += len(held)
                continue
            for id_ in held:
                ids = tuple(unique(itertools.chain(slot[id_], additions[id_])))
                if not _is_cache_order_stable(comodel, ids):
                    sorted_ids = comodel.browse(ids)._sorted_by_ids(
                        comodel._order, False
                    )
                    if sorted_ids is not None:
                        ids = sorted_ids
                slot[id_] = ids
            synced += len(held)
        if _debug.logic.enabled and (synced or evicted):
            _debug.logic(
                "field.x2many.scope_sync",
                model=self.model_name,
                field=self.name,
                records=len(additions),
                added=sum(len(added) for added in additions.values()),
                synced=synced,
                evicted=evicted,
            )

    def _evict_other_scopes(self, env: Environment, ids: Collection[IdType]) -> None:
        stored_ids = [id_ for id_ in ids if isinstance(id_, int)]
        if not stored_ids:
            return
        own = env.get_cache_key(self)
        evicted = 0
        for key, slot in list(env.core.iter_context_caches(self)):
            if key in (own, PENDING_SCOPE_KEY):
                continue
            for id_ in stored_ids:
                if slot.pop(id_, None) is not None:
                    evicted += 1
        if _debug.logic.enabled and evicted:
            _debug.logic(
                "field.x2many.scope_evict",
                model=self.model_name,
                field=self.name,
                records=len(stored_ids),
                evicted=evicted,
                writer_su=env.su,
            )

    @override
    def _insert_cache(self, records: ModelLike, values: Iterable) -> None:
        # a read nothing narrows answers what the superuser's own search
        # would: the value fills the reader's slot and the superuser's, so a
        # compute_sudo compute that follows serves from the cache instead of
        # fetching the relation once more for its scope
        env = records.env
        if env.su or not self._reads_as_superuser(env):
            super()._insert_cache(records, values)
            return
        values = list(values)
        super()._insert_cache(records, values)
        slot = env.core.get_context_data(self, self._superuser_scope_key(env))
        mirrored = 0
        for id_, value in zip(records._ids, values, strict=True):
            if isinstance(id_, int) and id_ not in slot:
                slot[id_] = value
                mirrored += 1
        if mirrored and _debug.logic.enabled:
            _debug.logic(
                "field.x2many.read_mirrored_to_superuser",
                model=self.model_name,
                field=self.name,
                records=len(records),
                mirrored=mirrored,
                uid=env.uid,
            )

    @override
    def _update_cache(
        self,
        records: ModelLike,
        cache_value: typing.Any,
        dirty: bool = False,
        *,
        keep_other_scopes: bool = False,
        created: bool = False,
    ) -> None:
        if not keep_other_scopes:
            if cache_value and not all(isinstance(id_, int) for id_ in cache_value):
                self._mirror_to_other_scopes(records.env, records._ids, cache_value)
            else:
                self._evict_other_scopes(records.env, records._ids)
                if not records.env.su and self._reads_as_superuser(records.env):
                    self._mirror_to_superuser_scope(
                        records.env, records._ids, cache_value
                    )
        if created:
            self._mirror_to_superuser_scope(records.env, records._ids, cache_value)
        field_patches = records.env.core.get_patches(self)
        if field_patches and not field_patches.keys().isdisjoint(records._ids):
            _debug.logic(
                "field.x2many.patches_applied",
                model=self.model_name,
                field=self.name,
                records=len(records),
                patched=sum(1 for id_ in records._ids if id_ in field_patches),
            )
            for record in records:
                ids = field_patches.pop(record.id, ())
                if ids:
                    value = tuple(unique(itertools.chain(cache_value, ids)))
                else:
                    value = cache_value
                super()._update_cache(record, value, dirty)
            return
        super()._update_cache(records, cache_value, dirty)

    @override
    def convert_to_cache(
        self, value: typing.Any, record: ModelLike, validate: bool = True
    ) -> tuple[int | NewId, ...]:
        if is_recordset(value):
            if validate and value._name != self.comodel_name:
                raise ValueError(f"Wrong value for {self}: {value}")
            ids = value._ids
            if record and not record.id:
                ids = tuple(it and NewId(it) for it in ids)
            return ids

        elif isinstance(value, (list, tuple)):
            comodel = record.env[self.comodel_name]
            if record and not record.id:

                def browse(it):
                    return comodel.browse((it and NewId(it),))
            else:
                browse = comodel.browse
            if record._has_origin:
                current = self._get_raw_ids(record.with_context(active_test=False))
            else:
                current = ()
            delta = CommandDelta.fold(value, lambda it: browse(it).id)
            if _debug.logic.enabled:
                _debug.logic(
                    "field.x2many.commands_to_cache",
                    model=self.model_name,
                    field=self.name,
                    record=record.id,
                    commands=len(value),
                    current=len(current),
                    created=len(delta.created),
                    updated=len(delta.updated),
                    replaced=delta.replaced,
                )
            line_ids = [comodel.new(vals, ref=ref).id for ref, vals in delta.created]
            for line_id, vals in delta.updated:
                line = comodel.browse((line_id,))
                if validate:
                    line.update(vals)
                else:
                    line._update_cache(vals, validate=False)
                line_ids.append(line.id)
            return typing.cast(
                "tuple[int | NewId, ...]", tuple(delta.get_final_ids(current, line_ids))
            )

        elif not value:
            return ()

        raise ValueError(f"Wrong value for {self}: {value}")

    def _get_raw_ids(self, record: ModelLike) -> tuple[IdType, ...]:
        # Reading the field drops inactive corecords under the field's own
        # active_test, which a caller's with_context(active_test=False) cannot
        # lift; a write deriving the new relation from the old must see all of it.
        env = record.env
        field_cache = self._get_cache(env)
        record_id = record.id
        if (
            not self.store
            and record_id not in field_cache
            and env.is_protected(self, record)
        ):
            # the compute assigning this field is running: there is no earlier
            # value to derive a delta from; the read would answer the empty value
            # and cache it, and a write that finds nothing changed relies on it
            self._update_cache(record, ())
            return ()
        record[self.name]
        # the read may have replaced the cache dict the memo hands out
        return self._get_cache(env)[record_id]

    @override
    def _get_origin_value(self, origin: BaseModel) -> BaseModel:
        return origin.env[self.comodel_name].browse(self._get_raw_ids(origin))

    def _prepare_read_context(self) -> dict:
        context = {
            key: value for key, value in self.context.items() if key != "active_test"
        }
        context["active_test"] = False
        return context

    def _prepare_corecords(
        self, env: Environment, ids: tuple[int | NewId, ...], prefetch_ids: typing.Any
    ) -> BaseModel:
        Comodel = env.registry[self.comodel_name]
        corecords = object.__new__(Comodel)
        corecords.env = env
        corecords._ids = ids
        corecords._prefetch_ids = prefetch_ids
        if Comodel._active_name and self.context.get(
            "active_test", env.context.get("active_test", True)
        ):
            corecords = corecords.filtered(Comodel._active_name).with_prefetch(
                prefetch_ids
            )
        return corecords

    @override
    def convert_to_record(
        self, value: tuple[int | NewId, ...], record: ModelLike
    ) -> BaseModel:
        return self._prepare_corecords(
            record.env, value, PrefetchX2many(record, self, value)
        )

    def convert_to_record_multi(
        self, values: list[tuple[int | NewId, ...]], records: BaseModel
    ) -> BaseModel:
        ids = tuple(unique(id_ for ids in values for id_ in ids))
        return self._prepare_corecords(
            records.env, ids, PrefetchX2many(records, self, ids)
        )

    @override
    def convert_to_read(
        self, value: BaseModel, record: ModelLike, use_display_name: bool = True
    ) -> list[int]:
        return value.ids

    @override
    def convert_to_write(
        self, value: typing.Any, record: ModelLike
    ) -> list[CommandValue] | typing.Literal[False]:
        if isinstance(value, tuple):
            value = record.env[self.comodel_name].browse(value)

        if is_recordset(value) and value._name == self.comodel_name:

            def get_origin(val):
                return val._origin if hasattr(val, "_origin") else val

            inv_names = {field.name for field in record.pool.field_inverses[self]}
            linked_ids: list[IdType] = []
            result: list[CommandValue] = [Command.set(linked_ids)]
            for rec in value:
                origin = rec._origin
                if not origin:
                    values = rec._convert_to_write(
                        {
                            name: rec[name]
                            for name in tuple(rec._cache)
                            if name not in inv_names
                        }
                    )
                    result.append(Command.create(values))
                else:
                    linked_ids.append(origin.id)
                    if rec != origin:
                        values = rec._convert_to_write(
                            {
                                name: val
                                for name in tuple(rec._cache)
                                if name not in inv_names
                                and get_origin(val := rec[name]) != origin[name]
                            }
                        )
                        if values:
                            result.append(Command.update(origin.id, values))
            return result

        if value is False or value is None:
            return [Command.clear()]

        if isinstance(value, list):
            return value

        raise ValueError(f"Wrong value for {self}: {value}")

    @override
    def convert_to_export(self, value: BaseModel, record: ModelLike) -> str:
        return ",".join(value.mapped("display_name")) if value else ""

    @override
    def convert_to_display_name(
        self, value: BaseModel, record: ModelLike
    ) -> str | typing.Literal[False]:
        raise NotImplementedError

    @override
    def get_depends(self, model: BaseModel) -> tuple[Iterable[str], Iterable[str]]:
        depends, depends_context = super().get_depends(model)
        depends_context = unique(itertools.chain(depends_context, ("access",)))
        if not self.compute and isinstance(domain := self.domain, (list, Domain)):
            domain = Domain(domain)
            domain_paths = list(_iter_domain_depend_paths(domain))
            depends = unique(
                itertools.chain(
                    depends,
                    (self.name + "." + path for path in domain_paths),
                )
            )
            if _debug.logic.enabled and domain_paths:
                _debug.logic(
                    "field.x2many.domain_depends",
                    model=self.model_name,
                    field=self.name,
                    paths=domain_paths,
                )
        return depends, depends_context

    @override
    def create(self, record_values: Collection[tuple[BaseModel, typing.Any]]) -> None:
        self.write_batch(record_values, True)

    @override
    def mark_dirty(self, records: BaseModel, value: typing.Any) -> None:
        records.env.remove_to_compute(self, records)
        self.write_batch([(records, value)])

    def write_batch(
        self,
        records_commands_list: Collection[tuple[BaseModel, typing.Any]],
        create: bool = False,
    ) -> None:
        normalized: list[tuple[BaseModel, list]] = []
        for recs, value in records_commands_list:
            if isinstance(value, tuple):
                value = [Command.set(value)]
            elif is_recordset(value) and value._name == self.comodel_name:
                value = [Command.set(value._ids)]
            elif value is False or value is None:
                value = [Command.clear()]
            elif (
                isinstance(value, list)
                and value
                and not isinstance(value[0], (tuple, list))
            ):
                value = [Command.set(tuple(value))]
            if not isinstance(value, list):
                raise ValueError(f"Wrong value for {self}: {value}")
            normalized.append((recs, value))

        if not normalized:
            return

        record_ids = {rid for recs, cs in normalized for rid in recs._ids}
        _debug.pipeline(
            "field.x2many.write_batch",
            model=self.model_name,
            field=self.name,
            records=len(record_ids),
            commands=sum(len(cmds) for _recs, cmds in normalized),
            real=all(record_ids),
            store=self.store,
            create=create,
        )
        if all(record_ids):
            if self.store:
                normalized = [(recs, cmds) for recs, cmds in normalized if cmds]
            if normalized:
                self.write_real(normalized, create)
        else:
            assert not any(record_ids), (
                f"{normalized} contains a mix of real and new records. It is not supported."
            )
            self.write_new(normalized)

    def write_real(
        self,
        records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]],
        create: bool = False,
    ) -> None:
        raise NotImplementedError

    def write_new(
        self,
        records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]],
    ) -> None:
        raise NotImplementedError

    def _get_writer_models(
        self, records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]]
    ) -> tuple[BaseModel, BaseModel]:
        model = records_commands_list[0][0].browse()
        comodel = model.env[self.comodel_name].with_context(**self.context)
        if not self.store and not any(
            command[0] in _COMODEL_WRITING_COMMANDS
            for _recs, commands in records_commands_list
            for command in commands
        ):
            return model, comodel
        return model, self._check_sudo_commands(comodel)

    def _check_sudo_commands(self, comodel: BaseModel) -> BaseModel:
        if comodel._allow_sudo_commands:
            return comodel
        default_env = comodel.env.transaction.default_env
        _debug.logic(
            "field.x2many.commands_demoted",
            model=self.model_name,
            field=self.name,
            comodel=comodel._name,
            uid=getattr(default_env, "uid", None),
        )
        if default_env is None:
            raise AccessError(
                comodel.env._(
                    "Cannot write %(field)s on %(model)s: the commands must run "
                    "as a real user and this transaction has no default "
                    "environment to name one.",
                    field=str(self),
                    model=comodel._name,
                )
            )
        return comodel.sudo(False).with_user(default_env.uid)

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
        assert field_expr == self.name, "Supporting condition only to field"
        comodel = model.env[self.comodel_name]
        if not self.store:
            raise ValueError(f"Cannot convert {self} to SQL because it is not stored")

        if operator in ("in", "not in"):
            operator = "any" if operator == "in" else "not any"
        assert operator in (
            "any",
            "not any",
            "any!",
            "not any!",
        ), f"Relational field {self} expects 'any' operator"
        exists = operator in ("any", "any!")

        if isinstance(value, COLLECTION_TYPES):
            value = OrderedSet(value)
            comodel = comodel.sudo().with_context(active_test=False)
            if False in value:
                if len(value) > 1:
                    in_operator = "in" if exists else "not in"
                    return SQL(
                        "(%s OR %s)" if exists else "(%s AND %s)",
                        self.condition_to_sql(
                            field_expr,
                            in_operator,
                            (False,),
                            model,
                            alias,
                            query,
                        ),
                        self.condition_to_sql(
                            field_expr,
                            in_operator,
                            value - {False},
                            model,
                            alias,
                            query,
                        ),
                    )
                value = comodel._search(Domain.TRUE)
                exists = not exists
            else:
                value = comodel.browse(value)._as_query(ordered=False)
        elif isinstance(value, SQL):
            comodel = comodel.sudo()
            value = Domain("id", "any", value)
        coquery = self._get_query_for_condition_value(model, comodel, operator, value)
        return self._condition_to_sql_relational(model, alias, exists, coquery, query)

    def _get_query_for_condition_value(
        self,
        model: BaseModel,
        comodel: BaseModel,
        operator: str,
        value: Domain | Query,
    ) -> Query:
        field_domain = self.get_comodel_domain(model)
        if isinstance(value, Domain):
            domain = value & field_domain
            comodel = comodel.with_context(**self.context)
            bypass_access = self.bypass_search_access or operator in (
                "any!",
                "not any!",
            )
            _debug.logic(
                "field.x2many.subquery",
                model=self.model_name,
                field=self.name,
                operator=operator,
                bypass_access=bypass_access,
                field_domain=not field_domain.is_true(),
            )
            query = comodel._search(domain, bypass_access=bypass_access)
            assert isinstance(query, Query)
            return query
        if isinstance(value, Query):
            domain = field_domain.optimize_full(comodel)
            if not domain.is_true():
                _debug.logic(
                    "field.x2many.subquery.field_domain_added",
                    model=self.model_name,
                    field=self.name,
                    operator=operator,
                )
                value.add_where(domain._to_sql(comodel, value.table, value))
            return value
        raise NotImplementedError(f"Cannot build query for {value}")

    def _condition_to_sql_relational(
        self,
        model: BaseModel,
        alias: str,
        exists: bool,
        coquery: Query,
        query: Query,
    ) -> SQL:
        raise NotImplementedError


class PrefetchX2many(Reversible):
    __slots__ = ("field", "ids", "record")

    def __init__(
        self,
        record: ModelLike,
        field: _RelationalMulti,
        ids: tuple[int | NewId, ...] = (),
    ) -> None:
        self.record = record
        self.field = field
        self.ids = ids

    def __iter__(self) -> Iterator[int | NewId]:
        field_cache = self.field._get_cache(self.record.env)
        return unique(
            itertools.chain(
                (
                    coid
                    for id_ in self.record._prefetch_ids
                    for coid in field_cache.get(id_, ())
                ),
                self.ids,
            )
        )

    def __reversed__(self) -> Iterator[int | NewId]:
        field_cache = self.field._get_cache(self.record.env)
        return unique(
            itertools.chain(
                (
                    coid
                    for id_ in reversed(self.record._prefetch_ids)
                    for coid in field_cache.get(id_, ())
                ),
                reversed(self.ids),
            )
        )
