import logging
import typing
from collections import deque
from contextlib import suppress
from weakref import WeakSet, WeakValueDictionary
from weakref import ref as weakref_ref

from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import OrmObserver, _OrmProfile, enabled_observers
from odoo.tools import OrderedSet, frozendict, reset_cached_properties

from ..components.cache import FieldCache
from ..components.compute import ComputeEngine
from ..components.core import OrmCore
from ..components.unit_of_work import UnitOfWork
from ..primitives import SUPERUSER_ID, NewId
from ._backend_memory import InMemoryBackend
from .backend import POSTGRES_BACKEND
from .recordset_cache import Cache
from .registry import Registry

if typing.TYPE_CHECKING:
    from odoo.db import BaseCursor

    from ..fields.base import Field
    from .environment import Environment

_logger = logging.getLogger("odoo.api")
_orm_cache = logging.getLogger("odoo.orm.cache")
_debug = DebugLog(__name__)

MAX_FIXPOINT_ITERATIONS = 1000
RECENT_ENVIRONMENTS = 8


def _is_new_id(record_id: object) -> bool:
    return isinstance(record_id, NewId)


class _EnvironmentSet(WeakSet):
    __slots__ = ("_index",)

    def __init__(self) -> None:
        super().__init__()
        self.data: OrderedSet = OrderedSet()
        self._index: WeakValueDictionary[tuple, Environment] = WeakValueDictionary()

    @staticmethod
    def key(uid: typing.Any, su: bool, context: typing.Any) -> tuple:
        return (uid, su, context)

    @staticmethod
    def matches(
        env: Environment, uid: typing.Any, su: bool, context: typing.Any
    ) -> bool:
        return (
            env.uid == uid
            and env.su == su
            and (env.context is context or env.context == context)
        )

    def add(self, env: Environment) -> None:
        super().add(env)
        self._index[self.key(env.uid, env.su, env.context)] = env

    def clear(self) -> None:
        super().clear()
        self._index.clear()

    def discard(self, env: Environment) -> None:
        super().discard(env)
        key = self.key(env.uid, env.su, env.context)
        if self._index.get(key) is env:
            del self._index[key]

    def get_environment(self, key: tuple) -> Environment | None:
        env = self._index.get(key)
        return env if env is not None and env in self else None


class Transaction:
    __slots__ = (
        "_cache_store",
        "_compute_engine",
        "_last_env",
        "_recent_envs",
        "_ref_cache",
        "backend",
        "cache",
        "core",
        "default_env",
        "envs",
        "observers",
        "prefetch_batch",
        "registry",
        "unit_of_work",
    )

    def __init__(self, registry: Registry, storage=None):
        self.registry = registry
        self.backend = (
            InMemoryBackend(storage) if storage is not None else POSTGRES_BACKEND
        )
        self.envs: _EnvironmentSet = _EnvironmentSet()
        self.default_env: Environment | None = None
        self._last_env: weakref_ref[Environment] | None = None
        # the index and the last-env fast path hold environments weakly, so a
        # transient one (record.sudo().field, in a loop) died with its
        # recordset and was rebuilt on the next call; a short strong ring
        # keeps the recent ones alive between those calls
        self._recent_envs: deque[Environment] = deque(maxlen=RECENT_ENVIRONMENTS)

        self._cache_store: FieldCache[Field] = FieldCache(
            dirty_factory=OrderedSet, on_detach=self._drop_field_cache_memos
        )

        self._compute_engine: ComputeEngine[Field] = ComputeEngine(
            pending_factory=OrderedSet
        )

        self.core: OrmCore[Field] = OrmCore(
            cache=self._cache_store, engine=self._compute_engine
        )

        self.unit_of_work: UnitOfWork[Field] = UnitOfWork(
            self._cache_store,
            self._compute_engine,
            max_iterations=MAX_FIXPOINT_ITERATIONS,
        )
        self.unit_of_work.set_recompute_order(self._get_live_recompute_order)

        self.cache = Cache(self)
        self._ref_cache: dict[tuple[str, int], bool] = {}
        self.prefetch_batch: tuple[str, tuple] | None = None

        self.observers: tuple[OrmObserver, ...] = enabled_observers()
        _debug.lifecycle(
            "transaction.new",
            db=registry.db_name,
            backend=type(self.backend).__name__,
            observers=len(self.observers),
        )

    def environment(
        self, cr: BaseCursor, uid: int | None, context: dict, su: bool = False
    ) -> Environment:
        if uid == SUPERUSER_ID:
            su = True
        last_ref = self._last_env
        last = last_ref() if last_ref is not None else None
        envs = self.envs
        if last is not None and envs.matches(last, uid, su, context):
            return last
        frozen_context = (
            context if isinstance(context, frozendict) else frozendict(context)
        )
        env = envs.get_environment(envs.key(uid, su, frozen_context))
        if env is None:
            from .environment import Environment

            env = Environment._interned(self, cr, uid, frozen_context, su)
            envs.add(env)
            self._adopt_default_env(env)
            _debug.lifecycle(
                "transaction.environment_interned",
                uid=uid,
                su=su,
                context_keys=len(frozen_context),
                envs=len(envs),
            )
            if _debug.lifecycle.enabled and len(envs) % 100 == 0:
                _debug.lifecycle(
                    "transaction.environment_keys",
                    envs=len(envs),
                    keys=",".join(sorted(frozen_context)),
                )
        self._last_env = weakref_ref(env)
        recent = self._recent_envs
        if env in recent:
            recent.remove(env)
        recent.append(env)
        return env

    def _adopt_default_env(self, env: Environment) -> None:
        if self.default_env is None and env.uid and isinstance(env.uid, int):
            self.default_env = env

    def flush(self, env: Environment | None = None) -> None:
        if env is not None:
            self._flush_as(env)
            return
        if self.default_env is not None:
            self._flush_as(self.default_env)
        elif (env := next(iter(self.envs), None)) is not None:
            _logger.warning(
                "Transaction.flush(): no default_env; flushing as SUPERUSER"
            )
            _debug.logic(
                "transaction.flush.superuser_fallback",
                db=self.registry.db_name,
                envs=len(self.envs),
            )
            try:
                self._flush_as(self.environment(env.cr, SUPERUSER_ID, {}))
            finally:
                self.default_env = None
        self._report_profilers()

    def _flush_as(self, env: Environment) -> None:
        prof = _OrmProfile(_orm_cache)

        def recompute_fn(field):
            env[field.model_name]._recompute_field(field)

        def flush_fn(model_names):
            with env.cr.pipeline():
                for model_name in model_names:
                    env[model_name].flush_model()

        result = self.unit_of_work.flush_until_converged(recompute_fn, flush_fn)
        _debug.pipeline(
            "transaction.flush",
            uid=env.uid,
            iterations=result.iterations,
            converged=result.converged,
            stalled=len(result.stalled_fields),
        )

        if not result.converged:
            remaining = result.stalled_fields
            _debug.logic(
                "transaction.flush.not_converged",
                uid=env.uid,
                iterations=result.iterations,
                stalled=remaining,
                tolerant=bool(env.context.get("tolerant_recompute")),
            )
            if env.context.get("tolerant_recompute"):
                _logger.error(
                    "flush_all() did not converge after %d iterations. "
                    "Stalled fields: %s (tolerant mode, continuing)",
                    result.iterations,
                    remaining,
                )
            else:
                raise RuntimeError(
                    f"flush_all() did not converge after "
                    f"{result.iterations} iterations.  "
                    f"Stalled fields: {remaining}\n\n"
                    f"This indicates a circular compute or flush dependency.  "
                    f"Use context key 'tolerant_recompute' to suppress."
                )

        prof.stop()
        prof.report(_orm_cache, "flush_all: %d iterations", result.iterations)

    def observe_operation(
        self,
        operation: str,
        model_name: str,
        record_count: int,
        fields: frozenset[str],
    ) -> None:
        for observer in self.observers:
            observer.on_operation(operation, model_name, record_count, fields)

    def observe_timing(
        self, operation: str, model_name: str, record_count: int, elapsed: float
    ) -> None:
        for observer in self.observers:
            observer.on_operation_done(operation, model_name, record_count, elapsed)

    def _report_profilers(self) -> None:
        for observer in self.observers:
            observer.report()
            observer.clear()

    def _drop_field_cache_memos(self) -> None:
        for env in self.envs:
            with suppress(AttributeError):
                del env._field_cache_memo

    def clear(self):
        _debug.lifecycle(
            "transaction.clear",
            db=self.registry.db_name,
            envs=len(self.envs),
            ref_cache=len(self._ref_cache),
        )
        self._cache_store.clear()
        self._compute_engine.clear()
        self._ref_cache.clear()
        self._last_env = None
        self._recent_envs.clear()
        if env := next(iter(self.envs), None):
            env.cr.cache.clear()

    def _get_live_recompute_order(self) -> dict[typing.Any, int]:
        registry = self.registry
        registry._get_field_triggers()
        return registry.model_graph.recompute_order

    def reset(self) -> None:
        _debug.lifecycle("transaction.reset", db=self.registry.db_name)
        self.registry = Registry(self.registry.db_name)
        for env in self.envs:
            reset_cached_properties(env)
        self.clear()

    def forget_refs_of(self, model_names: typing.Iterable[str]) -> int:
        ref_cache = self._ref_cache
        if not ref_cache:
            return 0
        names = set(model_names)
        keys = [key for key in ref_cache if key[0] in names]
        for key in keys:
            del ref_cache[key]
        return len(keys)

    def invalidate_field_data(self, *, keep_new_records: bool = False) -> None:
        _debug.lifecycle("transaction.invalidate_field_data", db=self.registry.db_name)
        self._cache_store.invalidate_all(keep=_is_new_id if keep_new_records else None)
        self._ref_cache.clear()
