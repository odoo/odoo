import inspect
import logging
import threading
import typing
from collections.abc import Collection

from odoo.db import schema as sql
from odoo.libs.debug_log import DebugLog
from odoo.libs.lru import LRU
from odoo.tools import SQL
from odoo.tools.constants import CACHES_BY_KEY, REGISTRY_CACHES
from odoo.tools.misc import format_frame

from ._registry_stubs import _RegistryStubs

if typing.TYPE_CHECKING:
    from odoo.db import BaseCursor

_logger = logging.getLogger("odoo.registry")
_debug = DebugLog(__name__)


def get_signaling_table_name(cache_name: str) -> str:
    return f"orm_signaling_{cache_name}"


SIGNALING_TABLES = tuple(
    get_signaling_table_name(cache_name) for cache_name in ["registry", *CACHES_BY_KEY]
)

# every request reads the eleven watermarks; the serial's last value answers in
# one sequence read each, where max(id) planned eleven subselects per call
_SEQUENCES_QUERY = SQL(
    "SELECT %s",
    SQL(", ").join(
        SQL("coalesce(pg_sequence_last_value(%s::regclass), 0)", f"{table}_id_seq")
        for table in SIGNALING_TABLES
    ),
)


class _RegistryCaches:
    __slots__ = ("lrus",)

    def __init__(self) -> None:
        self.lrus: dict[str, LRU] = {
            cache_name: LRU(cache_size)
            for cache_name, cache_size in REGISTRY_CACHES.items()
        }

    def clear_group(self, cache_name: str) -> None:
        for cache in CACHES_BY_KEY[cache_name]:
            self.lrus[cache].clear()

    def clear_all(self) -> None:
        for lru in self.lrus.values():
            lru.clear()


def _get_calling_frame(depth: int = 3) -> typing.Any:
    frame = inspect.currentframe()
    for _ in range(depth):
        if frame is None:
            return None
        frame = frame.f_back
    return frame


class _RegistrySignalingMixin(_RegistryStubs):
    __slots__ = ()

    registry_sequence: int
    cache_sequences: dict[str, int]
    _caches: _RegistryCaches
    _invalidation_flags: threading.local

    def _init_signaling_state(self) -> None:
        self._caches = _RegistryCaches()
        self.registry_sequence = -1
        self.cache_sequences = {}
        self._invalidation_flags = threading.local()

    @property
    def registry_invalidated(self) -> bool:
        return getattr(self._invalidation_flags, "registry", False)

    @registry_invalidated.setter
    def registry_invalidated(self, value: bool) -> None:
        self._invalidation_flags.registry = value
        # a caller flipping the flag by hand says nothing about which models it
        # changed, so the scope is the whole registry until the flag is cleared
        self._invalidation_flags.models = None if value else set()
        if _debug.logic.enabled and value:
            _debug.logic(
                "registry.invalidated_by_hand",
                caller=format_frame(_get_calling_frame(depth=2)),
            )

    @property
    def invalidated_model_names(self) -> set[str] | None:
        if not self.registry_invalidated:
            return set()
        return getattr(self._invalidation_flags, "models", None)

    def _note_invalidated_models(self, model_names: Collection[str] | None) -> None:
        known = self.invalidated_model_names
        self._invalidation_flags.registry = True
        self._invalidation_flags.models = (
            None if model_names is None or known is None else known | set(model_names)
        )

    @property
    def cache_invalidated(self) -> set[str]:
        try:
            return self._invalidation_flags.cache
        except AttributeError:
            names = self._invalidation_flags.cache = set()
            return names

    @property
    def cache_invalidation_generation(self) -> dict[str, int]:
        try:
            return self._invalidation_flags.cache_generation
        except AttributeError:
            generation = self._invalidation_flags.cache_generation = {}
            return generation

    @property
    def ormcache_lrus(self) -> dict[str, LRU]:
        return self._caches.lrus

    def _clear_cache_group(self, cache_name: str) -> None:
        self._caches.clear_group(cache_name)

    def _invalidate_cache_groups(self, cache_names: Collection[str]) -> None:
        if _debug.perf.enabled:
            _debug.perf.count(
                "registry.cache.invalidate_groups",
                groups=",".join(cache_names),
                entries=sum(
                    len(self._caches.lrus[cache])
                    for cache_name in cache_names
                    for cache in CACHES_BY_KEY[cache_name]
                ),
            )
        generation = self.cache_invalidation_generation
        for cache_name in cache_names:
            self._clear_cache_group(cache_name)
            self.cache_invalidated.add(cache_name)
            generation[cache_name] = generation.get(cache_name, 0) + 1

    def _log_invalidation(self, cache_names: Collection[str], level: int) -> None:
        if not _logger.isEnabledFor(level):
            return
        _logger.log(
            level,
            "Invalidating %s model caches from %s",
            ",".join(cache_names),
            format_frame(_get_calling_frame()),
        )

    def clear_cache(self, *cache_names: str) -> None:
        cache_names = cache_names or ("default",)
        for cache_name in cache_names:
            if cache_name not in CACHES_BY_KEY:
                raise ValueError(
                    f"clear_cache: invalid cache name {cache_name!r} — only "
                    f"composite group names can be cleared (sub-cache names "
                    f"like 'templates.cached_values' cannot); valid names: "
                    f"{', '.join(sorted(CACHES_BY_KEY))}"
                )
        self._invalidate_cache_groups(cache_names)
        self._log_invalidation(cache_names, logging.DEBUG)

    def _reset_cache_changes(self) -> None:
        if self.cache_invalidated:
            _debug.logic(
                "registry.cache.reset_changes", groups=sorted(self.cache_invalidated)
            )
            for cache_name in self.cache_invalidated:
                self._clear_cache_group(cache_name)
            self.cache_invalidated.clear()

    def _create_missing_signaling_tables(self, cr: BaseCursor) -> None:
        existing_sig_tables = tuple(sql.get_tables_existing(cr, SIGNALING_TABLES))
        for table_name in SIGNALING_TABLES:
            if table_name not in existing_sig_tables:
                _debug.lifecycle("registry.signaling.table_created", table=table_name)
                cr.execute(
                    SQL(
                        "CREATE TABLE IF NOT EXISTS %s (id SERIAL PRIMARY KEY, date TIMESTAMP DEFAULT now())",
                        SQL.identifier(table_name),
                    )
                )
                cr.execute(
                    SQL(
                        "INSERT INTO %s DEFAULT VALUES",
                        SQL.identifier(table_name),
                    )
                )

    def _load_sequences(self, cr: BaseCursor) -> None:
        db_registry_sequence, db_cache_sequences = self.get_sequences(cr)
        self.registry_sequence = db_registry_sequence
        self.cache_sequences.update(db_cache_sequences)

        _debug.lifecycle(
            "registry.signaling.sequences_loaded",
            sequence=db_registry_sequence,
            caches=len(db_cache_sequences),
        )
        _logger.debug(
            "Multiprocess load registry signaling: [Registry: %s] %s",
            self.registry_sequence,
            " ".join(f"[Cache {k}: {v}]" for k, v in self.cache_sequences.items()),
        )

    def get_sequences(self, cr: BaseCursor) -> tuple[int, dict[str, int]]:
        cr.execute(_SEQUENCES_QUERY)
        row = cr.fetchone()
        if row is None:
            raise RuntimeError("No result when reading signaling sequences")
        registry_sequence, *cache_sequences_values = row
        cache_sequences = dict(zip(CACHES_BY_KEY, cache_sequences_values, strict=True))
        return registry_sequence, cache_sequences

    def _sync_cache_sequences(self, db_cache_sequences: dict[str, int]) -> str:
        changes = ""
        invalidated = []
        for cache_name, cache_sequence in self.cache_sequences.items():
            expected_sequence = db_cache_sequences[cache_name]
            if expected_sequence > cache_sequence:
                _debug.logic(
                    "registry.signaling.cache_stale",
                    cache=cache_name,
                    local=cache_sequence,
                    db=expected_sequence,
                )
                for cache in CACHES_BY_KEY[cache_name]:
                    if cache not in invalidated:
                        invalidated.append(cache)
                        self._caches.lrus[cache].clear()
                self.cache_sequences[cache_name] = expected_sequence
                if _logger.isEnabledFor(logging.DEBUG):
                    changes += f"[Cache {cache_name} - {cache_sequence} -> {expected_sequence}]"
            elif expected_sequence < cache_sequence:
                _logger.debug(
                    "Ignoring stale cache signaling read for %s "
                    "(db %s < local %s), likely replica lag",
                    cache_name,
                    expected_sequence,
                    cache_sequence,
                )
        if invalidated:
            _logger.info(
                "Invalidating caches after database signaling: %s",
                sorted(invalidated),
            )
        return changes

    @staticmethod
    def _get_signalled_id(cr: BaseCursor, previous: int) -> int:
        row = cr.fetchone()
        if row and isinstance(row[0], int):
            return row[0]
        return previous + 1

    def _signal_registry_change(self, cr: BaseCursor) -> None:
        _logger.info("Registry changed, signaling through the database")
        cr.execute("INSERT INTO orm_signaling_registry DEFAULT VALUES RETURNING id")
        previous = self.registry_sequence  # debuglog
        self.registry_sequence = self._get_signalled_id(cr, self.registry_sequence)
        _debug.lifecycle(
            "registry.signaling.registry_signalled",
            previous=previous,
            sequence=self.registry_sequence,
        )

    def _signal_cache_changes(self, cr: BaseCursor) -> None:
        _logger.info(
            "Caches invalidated, signaling through the database: %s",
            sorted(self.cache_invalidated),
        )
        for cache_name in self.cache_invalidated:
            cr.execute(
                SQL(
                    "INSERT INTO %s DEFAULT VALUES RETURNING id",
                    SQL.identifier(get_signaling_table_name(cache_name)),
                )
            )
            self.cache_sequences[cache_name] = self._get_signalled_id(
                cr, self.cache_sequences[cache_name]
            )
