import functools
import logging
import os
import signal
import sys
import threading
import time
import typing
import warnings
from collections import defaultdict
from collections.abc import Callable, Collection, Mapping
from inspect import Parameter, signature
from typing import Any

from odoo.libs.debug_log import DebugLog

from .constants import REGISTRY_CACHES

C = typing.TypeVar("C", bound=Callable)

if typing.TYPE_CHECKING:
    from odoo.libs.lru import LRU
    from odoo.models import BaseModel

unsafe_eval = eval  # noqa: S307  ormcache key expressions built from code, not user input

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_RESERVED = "__ormcache_"
_METHOD_NAME = f"{_RESERVED}method"
_logger_lock = threading.RLock()
_logger_state: typing.Literal["wait", "abort", "run"] = "wait"


class TransactionMemo:
    __slots__ = ("factory", "invalidated_by", "key")

    _by_model: typing.ClassVar[
        defaultdict[str, list[tuple[TransactionMemo, frozenset[str] | None]]]
    ] = defaultdict(list)

    def __init__(
        self,
        key: str,
        *,
        invalidated_by: Collection[str] | Mapping[str, Collection[str]] = (),
        factory: Callable[[], Any] = dict,
    ) -> None:
        self.key = key
        self.factory = factory
        if isinstance(invalidated_by, Mapping):
            self.invalidated_by: dict[str, frozenset[str] | None] = {
                model_name: frozenset(field_names) if field_names else None
                for model_name, field_names in invalidated_by.items()
            }
        else:
            self.invalidated_by = dict.fromkeys(invalidated_by)
        for model_name, field_names in self.invalidated_by.items():
            self._by_model[model_name].append((self, field_names))

    def __call__(self, env: Any) -> Any:
        cr_cache = env.cr.cache
        try:
            return cr_cache[self.key]
        except KeyError:
            value = cr_cache[self.key] = self.factory()
            _debug.lifecycle("memo.created", key=self.key)
            return value

    def peek(self, env: Any) -> Any:
        return env.cr.cache.get(self.key)

    def discard(self, env: Any) -> None:
        env.cr.cache.pop(self.key, None)

    @classmethod
    def discard_for_model(
        cls, env: Any, model_name: str, written: Collection[str] | None = None
    ) -> None:
        memos = cls._by_model.get(model_name)
        if memos:
            cr_cache = env.cr.cache
            for memo, field_names in memos:
                if (
                    written is None
                    or field_names is None
                    or not field_names.isdisjoint(written)
                ):
                    if cr_cache.pop(memo.key, None) is not None:
                        _debug.lifecycle(
                            "memo.discarded",
                            key=memo.key,
                            model=model_name,
                            operation="write"
                            if written is not None
                            else "create_or_unlink",
                        )


class ormcache_counter:
    __slots__ = [
        "cache_name",
        "err",
        "gen_time",
        "hit",
        "miss",
        "tx_err",
        "tx_hit",
        "tx_miss",
    ]

    def __init__(self) -> None:
        self.hit: int = 0
        self.miss: int = 0
        self.err: int = 0
        self.gen_time: float = 0.0
        self.cache_name: str = ""
        self.tx_hit: int = 0
        self.tx_miss: int = 0
        self.tx_err: int = 0

    @property
    def ratio(self) -> float:
        return 100.0 * self.hit / (self.hit + self.miss or 1)

    @property
    def tx_ratio(self) -> float:
        return 100.0 * self.tx_hit / (self.tx_hit + self.tx_miss or 1)

    @property
    def tx_calls(self) -> int:
        return self.tx_hit + self.tx_miss


_COUNTERS: defaultdict[tuple[str, Callable], ormcache_counter] = defaultdict(
    ormcache_counter
)


def remove_counters(db_name: str) -> None:
    removed = 0  # debuglog
    for cache_key in [k for k in _COUNTERS if k[0] == db_name]:
        del _COUNTERS[cache_key]
        removed += 1  # debuglog
    _debug.lifecycle("cache.counters_removed", db=db_name, counters=removed)


_TX_STATS_ENABLED: bool = os.environ.get(
    "ODOO_ORMCACHE_TX_STATS", ""
).strip().lower() in ("1", "true", "yes", "on")


def _render_signature(method: Callable) -> tuple[str, dict[str, Any]]:
    rendered: list[str] = []
    arg_globals: dict[str, Any] = {}
    params = list(signature(method).parameters.values())
    prev_kind = None
    for index, param in enumerate(params):
        if (
            prev_kind == Parameter.POSITIONAL_ONLY
            and param.kind != Parameter.POSITIONAL_ONLY
        ):
            rendered.append("/")
        if param.kind == Parameter.KEYWORD_ONLY and prev_kind not in (
            Parameter.VAR_POSITIONAL,
            Parameter.KEYWORD_ONLY,
        ):
            rendered.append("*")

        if param.kind == Parameter.VAR_POSITIONAL:
            rendered.append(f"*{param.name}")
        elif param.kind == Parameter.VAR_KEYWORD:
            rendered.append(f"**{param.name}")
        elif param.default is Parameter.empty:
            rendered.append(param.name)
        else:
            placeholder = f"{_RESERVED}default_{index}"
            arg_globals[placeholder] = param.default
            rendered.append(f"{param.name}={placeholder}")
        prev_kind = param.kind

    if prev_kind == Parameter.POSITIONAL_ONLY:
        rendered.append("/")
    return ", ".join(rendered), arg_globals


class ormcache:
    key: Callable[..., tuple]

    def __init__(
        self,
        *args: str,
        cache: str = "default",
        skiparg: int | None = None,
    ) -> None:
        self.args = args
        self.skiparg = skiparg
        if cache not in REGISTRY_CACHES:
            raise ValueError(
                f"@ormcache(cache={cache!r}): unknown cache. Valid buckets: "
                f"{', '.join(sorted(REGISTRY_CACHES))}"
            )
        self.cache_name = cache
        if skiparg is not None:
            warnings.warn(
                "Deprecated since 19.0, ormcache(skiparg) will be removed",
                DeprecationWarning,
                stacklevel=2,
            )

    def __call__(self, method: C) -> C:
        assert not hasattr(self, "method"), "ormcache is already bound to a method"
        self.method = method
        self.set_key()
        assert self.key is not None, "ormcache.key not initialized"

        _key = self.key
        _method = method
        _cache_name = self.cache_name
        _counters = _COUNTERS
        _monotonic = time.monotonic
        _warn = _logger.warning
        _debug.lifecycle(
            "cache.bound",
            method=method.__qualname__,
            cache=self.cache_name,
            key_args=self.args,
            skiparg=self.skiparg,
        )

        @functools.wraps(method)
        def get_cached_result(*args, **kwargs):
            model = args[0]
            pool = model.pool
            d = pool.ormcache_lrus[_cache_name]
            key = _key(*args, **kwargs)
            counter = _counters[pool.db_name, _method]
            counter.cache_name = _cache_name

            if not _TX_STATS_ENABLED:
                try:
                    r = d[key]
                    counter.hit += 1
                    return r
                except KeyError:
                    counter.miss += 1
                except TypeError:
                    _warn("cache lookup error on %r", key, exc_info=True)
                    counter.err += 1
                    _debug.logic(
                        "cache.unhashable_key",
                        method=_method.__qualname__,
                        cache=_cache_name,
                    )
                    return _method(*args, **kwargs)
            else:
                cr_cache = model.env.cr.cache
                tx_lookups = cr_cache.get("_ormcache_lookups")
                if tx_lookups is None:
                    tx_lookups = set()
                    cr_cache["_ormcache_lookups"] = tx_lookups

                tx_first = False
                try:
                    tx_key = hash(key)
                    tx_first = tx_key not in tx_lookups
                    if tx_first:
                        tx_lookups.add(tx_key)
                    r = d[key]
                    counter.hit += 1
                    counter.tx_hit += int(tx_first)
                    return r
                except KeyError:
                    counter.miss += 1
                    counter.tx_miss += int(tx_first)
                except TypeError:
                    _warn("cache lookup error on %r", key, exc_info=True)
                    counter.err += 1
                    counter.tx_err += 1
                    _debug.logic(
                        "cache.unhashable_key",
                        method=_method.__qualname__,
                        cache=_cache_name,
                    )
                    return _method(*args, **kwargs)

            generation = d.generation
            start = _monotonic()
            value = _method(*args, **kwargs)
            elapsed = _monotonic() - start
            counter.gen_time += elapsed
            d.set_if_generation(key, value, generation)
            if _debug.perf.enabled:
                _debug.perf.count(
                    "cache.miss",
                    method=_method.__qualname__,
                    cache=_cache_name,
                    model=model._name,
                    ms=elapsed * 1000.0,
                    stale=d.generation != generation,
                    misses=counter.miss,
                )
            return value

        get_cached_result.__cache__ = self  # type: ignore[attr-defined]
        return typing.cast("C", get_cached_result)

    def add_value(
        self,
        *args: Any,
        cache_value: Any = None,
        generation: int | None = None,
        **kwargs: Any,
    ) -> None:
        model: BaseModel = args[0]
        d: LRU = model.pool.ormcache_lrus[self.cache_name]
        key = self.key(*args, **kwargs)
        if generation is None:
            d[key] = cache_value
        else:
            d.set_if_generation(key, cache_value, generation)
        _debug.lifecycle(
            "cache.value_added",
            method=self.method.__qualname__,
            cache=self.cache_name,
            pinned_generation=generation is not None,
            stale=generation is not None and d.generation != generation,
        )

    def get_cache_generation(self, model: BaseModel) -> int:
        return model.pool.ormcache_lrus[self.cache_name].generation

    def set_key(self) -> None:
        assert self.method is not None
        if self.skiparg is not None:
            self.key = lambda *args, **kwargs: (
                args[0]._name,
                self.method,
                *args[self.skiparg :],
            )
            return
        args, arg_globals = _render_signature(self.method)
        parameters = signature(self.method).parameters
        first_param = next(iter(parameters), None)
        if first_param is None:
            msg = (
                f"@ormcache cannot decorate {self.method.__qualname__}: it takes "
                f"no arguments, so the cache key has no record to key on. "
                f"ormcache decorates model methods, whose first parameter is the "
                f"recordset."
            )
            raise ValueError(msg)
        if colliding := sorted(p for p in parameters if p.startswith(_RESERVED)):
            msg = (
                f"@ormcache cannot decorate {self.method.__qualname__}: its "
                f"parameter(s) {', '.join(colliding)} use the reserved "
                f"{_RESERVED!r} prefix and would shadow the cache key."
            )
            raise ValueError(msg)
        values = [f"{first_param}._name", _METHOD_NAME, *self.args]
        code = f"lambda {args}: ({''.join(a for arg in values for a in (arg, ','))})"
        self.key = unsafe_eval(code, {_METHOD_NAME: self.method, **arg_globals})


class ormcache_context(ormcache):
    def __init__(self, *args: str, keys: tuple[str, ...], skiparg: None = None) -> None:
        assert skiparg is None, "ormcache_context() no longer supports skiparg"
        warnings.warn(
            "Since 19.0, use ormcache directly, context values are available as `self.env.context.get`",
            DeprecationWarning,
            stacklevel=2,
        )
        self.keys = keys
        super().__init__(*args)

    def set_key(self) -> None:
        assert self.method is not None
        sign = signature(self.method)
        cont_expr = (
            "(context or {})" if "context" in sign.parameters else "self.env.context"
        )
        keys_expr = "tuple(%s.get(k) for k in %r)" % (cont_expr, self.keys)
        self.args += (keys_expr,)
        super().set_key()


class _StatsLine:
    __slots__ = ["counter", "method", "nb_entries", "sz_entries_max", "sz_entries_sum"]

    def __init__(self, method: Callable, counter: ormcache_counter) -> None:
        self.sz_entries_sum: int = 0
        self.sz_entries_max: int = 0
        self.nb_entries: int = 0
        self.counter = counter
        self.method = method


type _CacheStats = defaultdict[str, dict[Callable, _StatsLine]]
type _CacheUsage = defaultdict[str, list[tuple[str, int, int, int]]]


def _keep_logging_ormcache_stats() -> bool:
    if _logger_state == "run":
        return True
    _logger.info("Stopping logging ORM cache stats")
    return False


def _get_ormcache_stats(show_size: bool) -> tuple[_CacheStats, _CacheUsage] | None:
    from odoo.modules.registry import Registry

    cache_stats: _CacheStats = defaultdict(dict)
    cache_usage: _CacheUsage = defaultdict(list)

    registries = Registry.registries.snapshot
    class_slots: dict[type, tuple[str, ...]] = {}
    for i, (dbname, registry) in enumerate(registries.items(), start=1):
        if not _keep_logging_ormcache_stats():
            return None
        _logger.info("Processing database %s (%d/%d)", dbname, i, len(registries))
        db_cache_stats = cache_stats[dbname]
        db_cache_usage = cache_usage[dbname]
        for cache_name, cache in registry.ormcache_lrus.items():
            cache_total_size = 0
            for cache_key, cache_value in cache.snapshot.items():
                method = cache_key[1]
                stats = db_cache_stats.get(method)
                if stats is None:
                    stats = db_cache_stats[method] = _StatsLine(
                        method, _COUNTERS[dbname, method]
                    )
                stats.nb_entries += 1
                if not show_size:
                    continue
                size = get_cache_size(
                    (cache_key, cache_value),
                    cache_info=method.__qualname__,
                    class_slots=class_slots,
                )
                cache_total_size += size
                stats.sz_entries_sum += size
                stats.sz_entries_max = max(stats.sz_entries_max, size)
            db_cache_usage.append(
                (cache_name, len(cache), cache.count, cache_total_size)
            )

    for (dbname, method), counter in _COUNTERS.copy().items():
        if not _keep_logging_ormcache_stats():
            return None
        db_cache_stats = cache_stats[dbname]
        if db_cache_stats.get(method) is None:
            db_cache_stats[method] = _StatsLine(method, counter)

    return cache_stats, cache_usage


def _ormcache_stats_header(show_size: bool) -> list[str]:
    log_msgs = ["Caches stats:"]
    if not _TX_STATS_ENABLED:
        log_msgs.append(
            "(TX Hit Ratio / TX Call disabled \u2014 set ODOO_ORMCACHE_TX_STATS=1"
            " to collect per-transaction stats)"
        )
    size_column_info = (
        (f"{'Memory %':>10},{'Memory SUM':>12},{'Memory MAX':>12},")
        if show_size
        else ""
    )
    log_msgs.append(
        f"{'Cache Name':>25},"
        f"{'Entry':>7},"
        f"{size_column_info}"
        f"{'Hit':>6},"
        f"{'Miss':>6},"
        f"{'Err':>6},"
        f"{'Gen Time [s]':>13},"
        f"{'Hit Ratio':>10},"
        f"{'TX Hit Ratio':>13},"
        f"{'TX Call':>8},"
        "  Method"
    )
    return log_msgs


def _ormcache_stats_row(stat: _StatsLine, sz_entries_all: int, show_size: bool) -> str:
    size_data = (
        (
            f"{stat.sz_entries_sum / (sz_entries_all or 1) * 100:9.1f}%,"
            f"{stat.sz_entries_sum:12d},"
            f"{stat.sz_entries_max:12d},"
        )
        if show_size
        else ""
    )
    return (
        f"{stat.counter.cache_name:>25},"
        f"{stat.nb_entries:7d},"
        f"{size_data}"
        f"{stat.counter.hit:6d},"
        f"{stat.counter.miss:6d},"
        f"{stat.counter.err:6d},"
        f"{stat.counter.gen_time:13.3f},"
        f"{stat.counter.ratio:9.1f}%,"
        f"{stat.counter.tx_ratio:12.1f}%,"
        f"{stat.counter.tx_calls:8d},"
        f"  {stat.method.__qualname__}"
    )


def _format_ormcache_stats(
    cache_stats: _CacheStats, cache_usage: _CacheUsage, show_size: bool
) -> list[str] | None:
    header = _ormcache_stats_header(show_size)
    column_info = header[-1]
    log_msgs = header[:-1]

    for dbname, db_cache_stats in sorted(
        cache_stats.items(), key=lambda k: k[0] or "~"
    ):
        if not _keep_logging_ormcache_stats():
            return None
        log_msgs.append(f"Database {dbname or '<no_db>'}:")
        log_msgs.extend(
            f" * {cache_name}: {entries}/{count}"
            f"{f' ({cache_total_size} bytes)' if cache_total_size else ''}"
            for cache_name, entries, count, cache_total_size in cache_usage[dbname]
        )
        log_msgs.append("Details:")

        db_cache_stat = sorted(
            db_cache_stats.items(), key=lambda k: (-k[1].sz_entries_sum, k[0].__name__)
        )
        sz_entries_all = sum(stat.sz_entries_sum for _, stat in db_cache_stat)
        log_msgs.append(column_info)
        log_msgs.extend(
            _ormcache_stats_row(stat, sz_entries_all, show_size)
            for _method, stat in db_cache_stat
        )
    return log_msgs


def _log_ormcache_stats(show_size: bool) -> None:
    global _logger_state  # noqa: PLW0603  process-wide cache-stats logging state
    try:
        collected = _get_ormcache_stats(show_size)
        if collected is None:
            return
        log_msgs = _format_ormcache_stats(*collected, show_size)
        if log_msgs is None:
            return
        _logger.info("\n".join(log_msgs))
        _debug.lifecycle("cache.stats_logged", lines=len(log_msgs), show_size=show_size)
    except Exception:
        _logger.exception("error while logging ormcache statistics")
    finally:
        with _logger_lock:
            _logger_state = "wait"


def log_ormcache_stats(
    sig: int | None = None,
    frame: Any = None,
) -> None:
    show_size = sig == signal.SIGUSR2
    if sig not in (None, signal.SIGUSR1, signal.SIGUSR2):
        return

    global _logger_state  # noqa: PLW0603  process-wide cache-stats logging state
    with _logger_lock:
        if _logger_state != "wait":
            _logger_state = "abort"
            _debug.logic("cache.stats_aborted", state=_logger_state, signal=sig)
            return
        _logger_state = "run"
    _debug.lifecycle("cache.stats_requested", signal=sig, show_size=show_size)

    threading.Thread(
        target=_log_ormcache_stats,
        args=(show_size,),
        name=(
            "odoo.signal.log_ormcache_stats_with_size"
            if show_size
            else "odoo.signal.log_ormcache_stats"
        ),
    ).start()


def get_cache_size(
    obj: Any,
    *,
    cache_info: str = "",
    seen_ids: set[int] | None = None,
    class_slots: dict[type, tuple[str, ...]] | None = None,
) -> int:
    from odoo.api import Environment
    from odoo.models import BaseModel

    if seen_ids is None:
        seen_ids = set(map(id, (None, False, True)))
    if class_slots is None:
        class_slots = {}
    total_size = 0
    objects = [obj]

    while objects:
        cur_obj = objects.pop()
        if id(cur_obj) in seen_ids:
            continue

        if cache_info and isinstance(cur_obj, (BaseModel, Environment)):
            _logger.error("%s is cached by %s", cur_obj, cache_info)
            _debug.logic(
                "cache.env_bound_value_cached",
                cache=cache_info,
                type=type(cur_obj).__name__,
            )
            continue

        seen_ids.add(id(cur_obj))
        total_size += sys.getsizeof(cur_obj)

        if hasattr(cur_obj, "__slots__"):
            cur_obj_cls = type(cur_obj)
            attributes = class_slots.get(cur_obj_cls)
            if attributes is None:
                class_slots[cur_obj_cls] = attributes = tuple(
                    {
                        (f"_{cls.__name__}{attr}" if attr.startswith("__") else attr)
                        for cls in cur_obj_cls.mro()
                        for attr in getattr(cls, "__slots__", ())
                    }
                )
            objects.extend(getattr(cur_obj, attr, None) for attr in attributes)
        if hasattr(cur_obj, "__dict__"):
            objects.append(cur_obj.__dict__)

        if isinstance(cur_obj, Mapping):
            objects.extend(cur_obj.values())
            objects.extend(cur_obj.keys())
        elif isinstance(cur_obj, Collection) and not isinstance(
            cur_obj, (str, bytes, bytearray)
        ):
            objects.extend(cur_obj)

    return total_size
