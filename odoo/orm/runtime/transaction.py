"""ORM Transaction — per-cursor state container.

A :class:`Transaction` owns the cache (:class:`FieldCache`), compute engine,
:class:`OrmCore` facade, :class:`UnitOfWork`, and profiling tools for a
single database cursor lifetime.  Created lazily on first
``Environment.__new__`` call for a cursor that has no transaction yet.
"""

import logging
import typing
from contextlib import suppress
from weakref import WeakSet

from odoo.tools import OrderedSet, reset_cached_properties
from odoo.tools.nplusone import NplusOneTracker, _n1_enabled
from odoo.tools.orm_profiler import OrmProfiler, _orm_profiling_enabled

from ..components.cache import FieldCache
from ..components.compute import ComputeEngine
from ..components.core import OrmCore
from ..components.unit_of_work import UnitOfWork
from .cache_compat import Cache
from .registry import Registry

if typing.TYPE_CHECKING:
    from .environment import Environment

_logger = logging.getLogger("odoo.api")

MAX_FIXPOINT_ITERATIONS = 10


class Transaction:
    """An object holding ORM data structures for a transaction."""

    __slots__ = (
        "_Transaction__file_open_tmp_paths",
        "_last_env",
        "_n1_tracker",
        "_orm_profiler",
        "_ref_cache",
        "cache",
        "cache_store",
        "compute_engine",
        "core",
        "default_env",
        "envs",
        "registry",
        "storage",
        "unit_of_work",
    )

    def __init__(self, registry: Registry, storage=None):
        self.registry = registry
        # Optional in-memory storage backend (DictBackend).  When set, ORM
        # CRUD methods dispatch to this backend instead of generating SQL.
        # ``None`` (default) means the normal PostgreSQL path via ``cr``.
        self.storage = storage
        # weak OrderedSet of environments
        self.envs: WeakSet[Environment] = WeakSet()
        self.envs.data = OrderedSet()  # type: ignore[attr-defined]
        # default environment (for flushing)
        self.default_env: Environment | None = None
        # MRU cache for fast env lookup (covers repeated with_user/sudo calls)
        self._last_env: Environment | None = None

        # Standalone cache component — owns the data structures for
        # cached field values, dirty tracking, and x2many patches.
        # The dirty factory is OrderedSet to preserve write order during flush.
        self.cache_store = FieldCache(dirty_factory=OrderedSet)

        # Standalone compute scheduling engine — owns pending recomputations
        # and field protection scopes.  OrderedSet ensures deterministic order.
        self.compute_engine = ComputeEngine(pending_factory=OrderedSet)

        # Layer 1 facade — flat API over cache + compute for internal ORM
        # consumers.  Accessed via env._core (cached_property on Environment).
        self.core = OrmCore(cache=self.cache_store, engine=self.compute_engine)

        # Standalone flush scheduling engine — convergence loop + stall detection.
        self.unit_of_work = UnitOfWork(
            self.cache_store,
            self.compute_engine,
            max_iterations=MAX_FIXPOINT_ITERATIONS,
        )
        # Wire topological recompute order from the registry's model graph.
        # This allows the UnitOfWork to process pending fields in dependency
        # order, reducing convergence iterations from O(depth) to O(1).
        if hasattr(registry, "model_graph"):
            self.unit_of_work.set_recompute_order(registry.model_graph.recompute_order)

        # backward-compatible view of the cache
        self.cache = Cache(self)
        # cache for env.ref() exists() results, keyed by (model_name, record_id)
        self._ref_cache: dict[tuple[str, int], bool] = {}

        # N+1 CRUD detection (None when disabled, zero overhead)
        self._n1_tracker: NplusOneTracker | None = (
            NplusOneTracker() if _n1_enabled else None
        )

        # Aggregate ORM profiler (None when disabled, zero overhead)
        self._orm_profiler: OrmProfiler | None = (
            OrmProfiler() if _orm_profiling_enabled else None
        )

        # temporary directories (managed in odoo.tools.file_open_temporary_directory)
        self.__file_open_tmp_paths = []  # type: ignore # noqa: PLE0237

    def flush(self) -> None:
        """Flush pending computations and updates in the transaction."""
        if self.default_env is not None:
            self.default_env.flush_all()
        else:
            from .environment import Environment

            for env in self.envs:
                _logger.warning("Missing default_env, flushing as public user")
                public_user = env.ref("base.public_user")
                Environment(env.cr, public_user.id, {}).flush_all()
                break
        # Report N+1 violations at end of request
        if self._n1_tracker is not None:
            self._n1_tracker.report()
            self._n1_tracker.clear()
        # Report aggregate ORM profile at end of request
        if self._orm_profiler is not None:
            self._orm_profiler.report()
            self._orm_profiler.clear()

    def clear(self):
        """Clear the caches and pending computations and updates in the transactions."""
        self.cache_store.clear()  # data + dirty + patches
        self.compute_engine.clear()  # pending recomputations
        self._ref_cache.clear()
        # reset per-env Field._get_cache() memos
        for env in self.envs:
            with suppress(AttributeError):
                del env._field_cache_memo
        self._last_env = None
        # all envs of the transaction share the same cursor
        if env := next(iter(self.envs), None):
            env.cr.cache.clear()

    def reset(self) -> None:
        """Reset the transaction.  This clears the transaction, and reassigns
        the registry on all its environments.  This operation is strongly
        recommended after reloading the registry.
        """
        self.registry = Registry(self.registry.db_name)
        for env in self.envs:
            reset_cached_properties(env)
        self.clear()

    def invalidate_field_data(self) -> None:
        """Invalidate the cache of all the fields.

        This operation is unsafe by default, and must be used with care.
        Indeed, invalidating a dirty field on a record may lead to an error,
        because doing so drops the value to be written in database.
        """
        self.cache_store.invalidate_all()
        self._ref_cache.clear()
        # reset Field._get_cache()
        for env in self.envs:
            with suppress(AttributeError):
                del env._field_cache_memo
