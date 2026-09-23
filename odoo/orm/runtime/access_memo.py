from __future__ import annotations

import typing
from collections import defaultdict
from contextlib import contextmanager

from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql.builder import SQL
from odoo.tools.query import Query

from ..constants import READ_GROUP_NUMBER_GRANULARITY
from ..domain import Domain, DomainBool, DomainCondition, DomainNary, DomainNot
from ..domain.constants import SUBDOMAIN_OPERATORS
from ..domain.optimizations import access_condition_target

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterator

    from ..fields import Field
    from ..models import BaseModel
    from .environment import Environment
    from .registry import Registry

_debug = DebugLog(__name__)

_MAX_DEPTH = 8

type Fact = tuple[str, str]
type Facts = frozenset[Fact] | None


def domain_read_facts(model: BaseModel, domain: Domain) -> Facts:
    # the (model, field) pairs whose values decide which records the domain
    # admits; None when some of it cannot be told (a custom SQL condition, a
    # subquery, a searchable compute that declares no dependency)
    facts: set[Fact] = set()
    try:
        known = _collect_domain(model, domain, facts, 0)
    except KeyError, TypeError, ValueError:
        known = False
    return frozenset(facts) if known else None


def _collect_domain(model: BaseModel, domain: Domain, facts: set, depth: int) -> bool:
    if isinstance(domain, DomainBool):
        return True
    if isinstance(domain, DomainNot):
        return _collect_domain(model, domain.child, facts, depth)
    if isinstance(domain, DomainNary):
        return all(_collect_domain(model, c, facts, depth) for c in domain.children)
    if isinstance(domain, DomainCondition):
        return _collect_condition(model, domain, facts, depth)
    return False


def _collect_condition(
    model: BaseModel, condition: DomainCondition, facts: set, depth: int
) -> bool:
    field = _collect_path(model, condition.field_expr, facts, depth)
    if field is False:
        return False
    if condition.operator == "access":
        return field is not None and _collect_access(
            model, field, condition, facts, depth
        )
    value = condition.value
    if isinstance(value, Domain):
        subdomain = value
    elif condition.operator in SUBDOMAIN_OPERATORS and isinstance(value, list | tuple):
        subdomain = Domain(value, internal=True)
    else:
        return not isinstance(value, Query | SQL)
    if field is None or not field.relational:
        return False
    return _collect_domain(model.env[field.comodel_name], subdomain, facts, depth + 1)


def _collect_access(
    model: BaseModel,
    field: Field,
    condition: DomainCondition,
    facts: set,
    depth: int,
) -> bool:
    # what the pointed-to model's security domain reads decides the condition
    if depth >= _MAX_DEPTH:
        return False
    owner = model.env[field.model_name]
    target = DomainCondition(field.name, "access", condition.value)
    comodel_name, operation = access_condition_target(target, owner)
    env = owner.sudo(False).env
    domain = env.registry.access_policy.security_domain(env, comodel_name, operation)
    return _collect_domain(env[comodel_name], domain, facts, depth + 1)


def _collect_path(
    model: BaseModel, path: str, facts: set, depth: int
) -> Field | typing.Literal[False] | None:
    names = path.split(".")
    field = None
    for index, name in enumerate(names):
        field = model._fields.get(name)
        if field is None:
            if (
                index
                and index == len(names) - 1
                and name in READ_GROUP_NUMBER_GRANULARITY
            ):
                return None
            return False
        if not _collect_field(model, field, facts, depth):
            return False
        if index < len(names) - 1:
            if not field.relational:
                return False
            model = model.env[field.comodel_name]
    return field


def _collect_field(model: BaseModel, field: Field, facts: set, depth: int) -> bool:
    facts.add((model._name, field.name))
    if field.is_one2many:
        facts.add((field.comodel_name, field.inverse_name))
    elif field.is_many2many:
        facts.update(_relation_siblings(model, field))
    if field.store:
        return True
    if depth >= _MAX_DEPTH:
        return False
    if field.related:
        return _collect_path(model, field.related, facts, depth + 1) is not False
    depends = model.pool.field_depends.get(field)
    if not depends:
        return False
    return all(
        _collect_path(model, dotted, facts, depth + 1) is not False
        for dotted in depends
    )


def _relation_siblings(model: BaseModel, field: Field) -> Iterator[Fact]:
    relation, column1, column2 = field.relation, field.column1, field.column2
    if not (relation and column1 and column2):
        return
    relations = model.pool.many2many_relations
    for columns in ((relation, column1, column2), (relation, column2, column1)):
        yield from relations.get(columns, ())


class AccessMemo:
    __slots__ = (
        "_epoch",
        "_everything",
        "_facts",
        "_observed",
        "_observing",
        "_registered",
        "_rewatch",
        "_verdicts",
        "_watchers",
    )

    def __init__(self) -> None:
        self._epoch: int | None = None
        self._observing: list[tuple[str, set[Fact]]] = []
        self.clear()

    def clear(self) -> None:
        self._facts: dict[tuple, Facts] = {}
        self._verdicts: dict[tuple, dict[typing.Any, bool]] = {}
        self._watchers: defaultdict[str, set] = defaultdict(set)
        self._everything: set = set()
        self._registered: dict[tuple, tuple[Environment, bool]] = {}
        self._rewatch: list[tuple[Field, Environment, bool]] = []
        self._observed: defaultdict[str, set[Fact]] = defaultdict(set)

    def _sync(self, registry: Registry) -> None:
        epoch = registry.cache_epoch
        if epoch == self._epoch:
            return
        if self._epoch is not None and (self._verdicts or self._registered):
            _debug.lifecycle(
                "access_memo.cache_epoch_changed",
                verdicts=len(self._verdicts),
                x2many=len(self._registered),
            )
        rewatch = self._rewatch + [
            (key[0], env, everything)
            for key, (env, everything) in self._registered.items()
        ]
        observed = self._observed
        self.clear()
        self._observed = observed
        self._rewatch = rewatch
        self._epoch = epoch

    def _flush_rewatch(self) -> None:
        rewatch, self._rewatch = self._rewatch, []
        for field, env, everything in rewatch:
            self.watch_x2many(env, field, everything)

    def read_facts(self, env: Environment, model_name: str) -> Facts:
        key = (env._read_access_key, model_name)
        try:
            return self._facts[key]
        except KeyError:
            pass
        domain = env.registry.access_policy.record_domain(env, model_name, "read")
        facts = self._facts[key] = domain_read_facts(env[model_name], domain)
        if facts is None:
            _debug.logic("access_memo.rule_untrackable", model=model_name, uid=env.uid)
        return facts

    def _watch(self, entry: typing.Any, facts: Facts, models: Collection[str]) -> None:
        if facts is None:
            self._everything.add(entry)
            return
        for model_name in {model_name for model_name, _fname in facts} | set(models):
            self._watchers[model_name].add(entry)

    def read_verdicts(self, env: Environment, model_name: str) -> dict:
        self._sync(env.registry)
        key = (env._read_access_key, model_name)
        verdicts = self._verdicts.get(key)
        if verdicts is None:
            verdicts = self._verdicts[key] = {}
            self._watch(key, self.read_facts(env, model_name), ())
        return verdicts

    def cached_verdicts(self, env: Environment, model_name: str) -> dict | None:
        if self._epoch != env.registry.cache_epoch:
            return None
        return self._verdicts.get((env._read_access_key, model_name))

    def watch_x2many(self, env: Environment, field: Field, everything: bool) -> None:
        self._sync(env.registry)
        key = (field, env._read_access_key)
        if key in self._registered:
            return
        self._registered[key] = (env, everything)
        try:
            facts = None if everything else self.read_facts(env, field.comodel_name)
        except AccessError:
            facts = None
        self._watch(field, facts, self._observed_models(field.comodel_name))

    def _observed_models(self, model_name: str) -> set[str]:
        return {name for name, _fname in self._observed.get(model_name, ())}

    def observed_facts(self, model_name: str) -> Collection[Fact]:
        return self._observed.get(model_name, ())

    @contextmanager
    def observing(self, model_name: str) -> Iterator[None]:
        seen: set[Fact] = set()
        self._observing.append((model_name, seen))
        try:
            yield
        finally:
            self._observing.pop()
            new = seen - self._observed[model_name]
            if new:
                self._observed[model_name] |= new
                models = {name for name, _fname in new}
                for field, _scope in self._registered:
                    if field.comodel_name == model_name:
                        self._watch(field, frozenset(), models)

    def note_search(self, model_name: str, query: Query) -> None:
        if not self._observing:
            return
        seen = self._observing[-1][1]
        seen.add((model_name, "id"))
        for sql in (query.from_clause, query.where_clause):
            seen.update((field.model_name, field.name) for field in sql.to_flush)

    def written(
        self,
        env: Environment,
        model_name: str,
        fnames: Collection[str] | None,
        *,
        created: bool = False,
    ) -> list[Field]:
        # drops the verdicts the write may have changed, and answers the
        # x2many fields whose user slots may read through the written model
        self._sync(env.registry)
        if self._rewatch:
            self._flush_rewatch()
        entries = self._watchers.get(model_name, set()) | self._everything
        if not entries:
            return []
        self._drop_verdicts(entries, model_name, fnames, created)
        return [entry for entry in entries if not isinstance(entry, tuple)]

    def forget(
        self, env: Environment, model_name: str, fnames: Collection[str] | None
    ) -> None:
        # a cache invalidation says the rows may differ from what was read
        if not self._verdicts or self._epoch != env.registry.cache_epoch:
            return
        if fnames is None:
            for key in [key for key in self._verdicts if key[1] == model_name]:
                del self._verdicts[key]
        entries = self._watchers.get(model_name, set()) | self._everything
        self._drop_verdicts(entries, model_name, fnames, False)

    def _drop_verdicts(
        self,
        entries: Collection,
        model_name: str,
        fnames: Collection[str] | None,
        created: bool,
    ) -> None:
        dropped = 0
        for entry in entries:
            if not isinstance(entry, tuple) or entry not in self._verdicts:
                continue
            if created and entry[1] == model_name:
                continue
            facts = self._facts.get(entry)
            if (
                facts is None
                or fnames is None
                or any((model_name, fname) in facts for fname in fnames)
            ):
                del self._verdicts[entry]
                dropped += 1
        if dropped and _debug.logic.enabled:
            _debug.logic(
                "access_memo.verdicts_dropped",
                model=model_name,
                fields=None if fnames is None else sorted(fnames),
                dropped=dropped,
            )
