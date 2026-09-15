import threading
import typing
from contextlib import closing
from dataclasses import dataclass
from functools import lru_cache, partial

from psycopg import sql as psycopg_sql

from odoo.db import FunctionStatus, get_unaccent_status, has_trigram
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

from ._registry_stubs import _RegistryStubs

_debug = DebugLog(__name__)

if typing.TYPE_CHECKING:
    from odoo.db import BaseCursor

    from .environment import Environment


def _unaccent(
    x: SQL | str | psycopg_sql.Composable,
) -> SQL | str | psycopg_sql.Composed:
    if isinstance(x, SQL):
        return SQL("unaccent(%s)", x)
    if isinstance(x, psycopg_sql.Composable):
        return psycopg_sql.SQL("unaccent({})").format(x)
    return f"unaccent({x})"


@dataclass(frozen=True)
class _TextTransforms:
    unaccent_enabled: bool
    unaccent: dict[int, str]
    ilike: dict[int, str] | None


class _TextTables:
    by_db: dict[str, _TextTransforms] = {}
    # one build per process and database: a cold process whose threads all
    # meet their first ilike at once must not each scan the code points
    build_lock = threading.Lock()


def _get_text_transforms(
    cr: BaseCursor, db_name: str, unaccent_enabled: bool
) -> _TextTransforms:
    cached = _TextTables.by_db.get(db_name)
    if cached is not None and cached.unaccent_enabled == unaccent_enabled:
        return cached
    with _TextTables.build_lock:
        cached = _TextTables.by_db.get(db_name)
        if cached is not None and cached.unaccent_enabled == unaccent_enabled:
            return cached
        return _reset_text_transforms(cr, db_name, unaccent_enabled)


def _reset_text_transforms(
    cr: BaseCursor, db_name: str, unaccent_enabled: bool
) -> _TextTransforms:
    with _debug.perf(
        "registry.text_transforms.built", cr=cr, db=db_name, unaccent=unaccent_enabled
    ) as span:
        cr.execute(
            "SELECT datlocprovider FROM pg_database WHERE datname = current_database()"
        )
        provider = cr.fetchone()
        assert provider is not None
        # Other providers can lowercase contextually, so a character table is insufficient.
        context_free = provider[0] == "c"
        unaccent = SQL("unaccent(source)") if unaccent_enabled else SQL("source")
        folded = SQL("lower(%s)", unaccent) if context_free else SQL("source")
        # PostgreSQL text excludes NUL and Unicode surrogate code points.
        cr.execute(
            SQL(
                """
            WITH chars AS (
                SELECT chr(code) AS source FROM generate_series(1, 55295) AS code
                UNION ALL
                SELECT chr(code) AS source FROM generate_series(57344, 1114111) AS code
            )
            SELECT source, %(unaccent)s AS unaccented, %(folded)s AS folded
            FROM chars WHERE source <> %(unaccent)s OR source <> %(folded)s
            """,
                unaccent=unaccent,
                folded=folded,
            )
        )
        unaccent_table = {}
        ilike_table = {}
        for row in cr.dictfetchall():
            code = ord(row["source"])
            if row["unaccented"] != row["source"]:
                unaccent_table[code] = row["unaccented"]
            if row["folded"] != row["source"]:
                ilike_table[code] = row["folded"]
        transforms = _TextTransforms(
            unaccent_enabled, unaccent_table, ilike_table if context_free else None
        )
        span.set(
            context_free=context_free,
            unaccent_table=len(unaccent_table),
            ilike_table=len(ilike_table),
        )
    _TextTables.by_db[db_name] = transforms
    return transforms


def clear_text_transforms(db_name: str) -> None:
    _TextTables.by_db.pop(db_name, None)


def clear_all_text_transforms() -> None:
    _TextTables.by_db.clear()


def _identity(x: typing.Any) -> typing.Any:
    return x


def _translate_python(x: str, table: dict[int, str]) -> str:
    return x.translate(table)


class _RegistryCapabilitiesMixin(_RegistryStubs):
    __slots__ = ()

    has_unaccent: FunctionStatus

    has_trigram: bool
    unaccent: typing.Callable[..., SQL | str | psycopg_sql.Composed]

    _text_transforms: _TextTransforms | None

    def _probe_capabilities(self, cr: BaseCursor, db_name: str) -> None:
        self.has_unaccent = get_unaccent_status(cr)
        self.has_trigram = has_trigram(cr)
        self.unaccent = _unaccent if self.has_unaccent else _identity
        # the character tables cost a scan of every code point; a process that
        # never filters records in memory with ilike never needs them
        cached = _TextTables.by_db.get(db_name)
        self._text_transforms = (
            cached
            if cached is not None and cached.unaccent_enabled == bool(self.has_unaccent)
            else None
        )
        _debug.lifecycle(
            "registry.capabilities_probed",
            db=db_name,
            unaccent=self.has_unaccent.name,
            trigram=self.has_trigram,
            text_transforms_cached=self._text_transforms is not None,
        )

    def _get_text_transforms(self, cr: BaseCursor | None = None) -> _TextTransforms:
        transforms = self._text_transforms
        if transforms is None:
            unaccent_enabled = bool(self.has_unaccent)
            if cr is not None:
                transforms = _get_text_transforms(cr, self.db_name, unaccent_enabled)
            else:
                with closing(self.cursor()) as own_cr:
                    transforms = _get_text_transforms(
                        own_cr, self.db_name, unaccent_enabled
                    )
            self._text_transforms = transforms
        return transforms

    @property
    def unaccent_python(self) -> typing.Callable[[str], str]:
        if not self.has_unaccent:
            return _identity
        return partial(_translate_python, table=self._get_text_transforms().unaccent)

    def get_ilike_normalizer(self, env: Environment) -> typing.Callable[[str], str]:
        transforms = self._text_transforms or self._get_text_transforms(env.cr)
        ilike_table = transforms.ilike
        if ilike_table is not None:
            return partial(_translate_python, table=ilike_table)

        @lru_cache(maxsize=256)
        def normalize(value: str) -> str:
            expression = self.unaccent(SQL("%s", value))
            return env.execute_query(SQL("SELECT lower(%s)", expression))[0][0]

        return normalize
