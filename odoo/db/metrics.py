from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import SQL

from .errors import CURSOR_LOGGER_NAME

_logger = logging.getLogger(CURSOR_LOGGER_NAME)
_debug = DebugLog(__name__)

sql_counter: int = 0


if TYPE_CHECKING:
    import threading
    from collections.abc import Iterator
    from typing import Protocol

    class _MetricsHost(Protocol):
        _thread: threading.Thread

        sql_log_count: int
        sql_statement_count: int


class _MetricsMixin:
    sql_from_log: dict[str, tuple[int, float]]
    sql_into_log: dict[str, tuple[int, float]]
    sql_log_count: int
    sql_statement_count: int

    def _init_metrics_state(self) -> None:
        self.sql_from_log = {}
        self.sql_into_log = {}
        self.sql_log_count = 0
        self.sql_statement_count = 0

    def _format_statement(self, query: Any, params: Any = None) -> str:
        if isinstance(query, SQL):
            query, params = query.code, query.params
        if params is None:
            return str(query)
        try:
            if isinstance(params, dict):
                return str(query) % {k: repr(v) for k, v in params.items()}
            return str(query) % tuple(repr(v) for v in params)
        except Exception:
            return f"{query} [{params!r}]"

    def _record_metrics(
        self: _MetricsHost,
        delay: float,
        count: int = 1,
        *,
        statement: bool = True,
        query: Any = None,
        params: Any = None,
        start: float = 0.0,
        hooks: Any = None,
    ) -> None:
        global sql_counter  # noqa: PLW0603  process-wide SQL counter; the module IS the accumulator
        self.sql_log_count += count
        if statement:
            self.sql_statement_count += 1
        sql_counter += count
        t: Any = self._thread
        # http.application sets the pair together on a request thread; one
        # question answers for both.
        if hasattr(t, "query_count"):
            t.query_count += count
            t.query_time += delay
        for hook in hooks or ():
            hook(self, query, params, start, delay)

    def _record_sql_log(self, query_type: str, table: str | None, delay: float) -> None:
        if query_type == "into":
            log_target = self.sql_into_log
        elif query_type == "from":
            log_target = self.sql_from_log
        else:
            return
        stat_count, stat_time = log_target.get(table or "", (0, 0))
        log_target[table or ""] = (stat_count + 1, stat_time + delay * 1e6)

    @contextmanager
    def _enable_logging(self) -> Iterator[None]:
        """Force this cursor's queries to be logged for the duration of the block.

        Restores the level afterwards. The logger is process-wide, so this is not
        thread-safe -- it exists for a test that has just failed an
        `assertQueryCount` and wants to see which queries ran, which is worth more
        than isolation at that moment.
        """
        level = _logger.level
        _logger.setLevel(logging.DEBUG)
        _debug.lifecycle("metrics.sql_logging_forced", previous_level=level)
        try:
            yield
        finally:
            _logger.setLevel(level)
            _debug.lifecycle("metrics.sql_logging_restored", level=level)

    def log_sql_stats(self) -> None:
        _debug.perf.count(
            "metrics.cursor_totals",
            statements=self.sql_statement_count,
            rows=self.sql_log_count,
            from_tables=len(self.sql_from_log),
            into_tables=len(self.sql_into_log),
            process_rows=sql_counter,
        )
        if not _logger.isEnabledFor(logging.DEBUG):
            return

        def log_direction_stats(log_type: str) -> None:
            sqllogs = {"from": self.sql_from_log, "into": self.sql_into_log}
            sqllog = sqllogs[log_type]
            total = 0.0
            if sqllog:
                _logger.debug("SQL LOG %s:", log_type)
                for table, (stat_count, stat_time) in sorted(
                    sqllog.items(), key=lambda kv: kv[1][1], reverse=True
                ):
                    delay = timedelta(microseconds=stat_time)
                    _logger.debug("table: %s: %s/%s", table, delay, stat_count)
                    total += stat_time
                sqllog.clear()
            total_delay = timedelta(microseconds=total)
            _logger.debug(
                "SUM %s:%s/%d [%d]",
                log_type,
                total_delay,
                self.sql_log_count,
                sql_counter,
            )

        log_direction_stats("from")
        log_direction_stats("into")
        self.sql_log_count = 0


re_from = re.compile(
    r'\bfrom\s+(?:"?[a-zA-Z_0-9]+"?\.)?"?([a-zA-Z_0-9]+)\b', re.IGNORECASE
)
re_into = re.compile(
    r'\binto\s+(?:"?[a-zA-Z_0-9]+"?\.)?"?([a-zA-Z_0-9]+)\b', re.IGNORECASE
)
re_update = re.compile(
    r'^\s*update\s+(?:"?[a-zA-Z_0-9]+"?\.)?"?([a-zA-Z_0-9]+)\b', re.IGNORECASE
)
re_delete = re.compile(r"^\s*delete\b", re.IGNORECASE)

re_cte_start = re.compile(r"\s*with\s+(recursive\s+)?", re.IGNORECASE)
re_cte_name = re.compile(
    r'\s*"?[a-zA-Z_][a-zA-Z_0-9]*"?\s*(\([^)]*\))?\s*as\s*', re.IGNORECASE
)
re_cte_comma = re.compile(r"\s*,\s*")


def _split_ctes(decoded_query: str) -> tuple[int, list[str]]:
    m = re_cte_start.match(decoded_query)
    if not m:
        return 0, []
    pos = m.end()
    length = len(decoded_query)
    bodies: list[str] = []
    while True:
        m_name = re_cte_name.match(decoded_query, pos)
        if not m_name:
            return 0, []
        pos = m_name.end()
        if pos >= length or decoded_query[pos] != "(":
            return 0, []
        depth = 0
        start = pos
        while pos < length:
            char = decoded_query[pos]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    pos += 1
                    break
            pos += 1
        else:
            return 0, []
        bodies.append(decoded_query[start + 1 : pos - 1])
        m_comma = re_cte_comma.match(decoded_query, pos)
        if not m_comma:
            return pos, bodies
        pos = m_comma.end()


_NESTED = "\x00"

re_from_keyword = re.compile(r"\bfrom\b", re.IGNORECASE)


def _mask_nested_parentheses(sql_text: str) -> str:
    out = []
    depth = 0
    for char in sql_text:
        if char == "(":
            depth += 1
            out.append(_NESTED)
        elif char == ")":
            depth -= 1
            out.append(_NESTED)
        else:
            out.append(_NESTED if depth > 0 else char)
    return "".join(out)


def _match_from_clause(body: str) -> re.Match | None:
    masked = _mask_nested_parentheses(body)
    match = re_from.search(masked)
    if match is not None:
        return match
    if re_from_keyword.search(masked) is not None:
        return re_from.search(body)
    return None


def _classify_write_statement(body: str) -> tuple[str, str] | tuple[str, None] | None:
    res_update = re_update.match(body)
    if res_update:
        return "into", res_update.group(1)

    if re_delete.match(body):
        res_from = _match_from_clause(body)
        return ("into", res_from.group(1)) if res_from else ("other", None)

    res_into = re_into.search(body)
    if res_into:
        return "into", res_into.group(1)

    return None


def classify_query(decoded_query: str) -> tuple[str, str] | tuple[str, None]:
    offset, cte_bodies = _split_ctes(decoded_query)
    body = decoded_query[offset:]

    for cte_body in cte_bodies:
        cte_write = _classify_write_statement(cte_body)
        if cte_write is not None:
            _debug.logic(
                "metrics.cte_write_classified",
                ctes=len(cte_bodies),
                kind=cte_write[0],
                table=cte_write[1],
            )
            return cte_write

    write = _classify_write_statement(body)
    if write is not None:
        return write

    res_from = _match_from_clause(body)
    if res_from:
        return "from", res_from.group(1)

    return "other", None
