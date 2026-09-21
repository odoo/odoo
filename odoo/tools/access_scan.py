__all__ = [
    "get_accessible_ids",
    "get_accessible_query",
    "get_inaccessible_owners",
    "prepare_document_access_error",
    "stable_order",
]

import functools
import typing
from collections.abc import Callable, Collection, Generator, Iterable, Sequence
from typing import Any

from odoo.exceptions import AccessError, MissingError
from odoo.libs.collections import OrderedSet
from odoo.libs.debug_log import DebugLog
from odoo.tools.query import Query

if typing.TYPE_CHECKING:
    from odoo import api, models
    from odoo.api import DomainType

_debug = DebugLog(__name__)


def prepare_document_access_error(
    records: models.BaseModel, operation: str
) -> AccessError:
    return AccessError(
        records.env._(
            "The requested operation cannot be completed due to security "
            "restrictions. Please contact your system administrator.\n\n"
            "(Document type: %(type)s, Operation: %(operation)s)\n\n"
            "Records: %(records)s, User: %(user)s",
            type=records._description,
            operation=operation,
            records=records.ids[:6],
            user=records.env.uid,
        )
    )


def stable_order(order: str | None, tiebreak: str = "id ASC") -> str | None:
    if order and not any(term.strip().split()[0] == "id" for term in order.split(",")):
        return f"{order}, {tiebreak}"
    return order


def prepare_column_fetcher(
    model: models.BaseModel, fnames: Sequence[str]
) -> Callable[[Query], list[tuple]]:
    def fetch(query: Query) -> list[tuple]:
        return model.env.execute_query(
            query.select(
                *[model._field_to_sql(model._table, fname) for fname in fnames]
            )
        )

    return fetch


def get_accessible_ids(
    model: models.BaseModel,
    domain: DomainType,
    offset: int,
    limit: int | None,
    order: str | None,
    base_search: Callable[..., Query],
    *,
    fetch: Callable[[Query], Sequence[Sequence[Any]]],
    allowed: Callable[[Sequence[Sequence[Any]]], Iterable[int]],
    chunk_min: int,
    chunk_max: int,
    tiebreak: str = "id ASC",
    **kwargs,
) -> list[int]:
    scan_order = stable_order(order or model._order, tiebreak)

    if limit is None or limit is False:
        target = None
    elif limit is True:
        target = offset + 1
    elif limit == 0:
        return []
    else:
        target = offset + limit
    chunk = None if target is None else min(max(target, chunk_min), chunk_max)

    ordered: list[int] = []
    seen: set[int] = set()
    sql_offset = 0
    passes = 0  # debuglog
    while True:
        query = base_search(
            domain, offset=sql_offset, limit=chunk, order=scan_order, **kwargs
        )
        rows = fetch(query)
        chunk_allowed = set(allowed(rows))
        for row in rows:
            id_ = row[0]
            if id_ in chunk_allowed and id_ not in seen:
                seen.add(id_)
                ordered.append(id_)

        got = len(rows)
        sql_offset += got
        passes += 1  # debuglog
        if target is None or chunk is None or len(ordered) >= target or got < chunk:
            break
        chunk = min(chunk * 2, chunk_max)

    _debug.perf.count(
        "access_scan",
        model=model._name,
        target=target,
        passes=passes,
        scanned=sql_offset,
        allowed=len(ordered),
        last_chunk=chunk,
    )
    return ordered[offset:target]


class _RescannedCountQuery(Query):
    __slots__ = ("_rescan",)
    _rescan: Callable[[int | None], list[int]]

    def count_matching(self, limit: int | None = None) -> int:
        return len(self._rescan(limit))


def get_accessible_query(
    model: models.BaseModel,
    domain: DomainType,
    offset: int,
    limit: int | None,
    order: str | None,
    base_search: Callable[..., Query],
    *,
    fetch: Callable[[Query], Sequence[Sequence[Any]]],
    allowed: Callable[[Sequence[Sequence[Any]]], Iterable[int]],
    chunk_min: int,
    chunk_max: int,
    tiebreak: str = "id ASC",
    **kwargs,
) -> Query:
    scan = functools.partial(
        get_accessible_ids,
        model,
        domain,
        base_search=base_search,
        fetch=fetch,
        allowed=allowed,
        chunk_min=chunk_min,
        chunk_max=chunk_max,
        tiebreak=tiebreak,
        **kwargs,
    )
    query = _RescannedCountQuery(model.env, model._table, model._table_sql)
    query.set_result_ids(scan(offset=offset, limit=limit, order=order))
    query._rescan = lambda count_limit: scan(offset=0, limit=count_limit, order=order)
    return query


def get_inaccessible_owners(
    env: api.Environment,
    model_and_ids: dict[Any, Collection[int]],
    operation: str,
) -> Generator[tuple[str, int]]:
    if env.su:
        return
    for res_model, res_ids in model_and_ids.items():
        res_ids = OrderedSet(filter(None, res_ids))
        if not res_model or not res_ids:
            continue
        if res_model not in env:
            _debug.logic(
                "comodel_unknown",
                model=res_model,
                operation=operation,
                count=len(res_ids),
            )
            for res_id in res_ids:
                yield res_model, res_id
            continue
        if res_model == "res.users" and env.uid in res_ids:
            res_ids = OrderedSet(rid for rid in res_ids if rid != env.uid)
            if not res_ids:
                continue
        records = env[res_model].browse(res_ids)
        try:
            records = records._filtered_access(operation)
        except MissingError:
            _debug.logic("comodel_records_missing", model=res_model)
            records = records.exists()._filtered_access(operation)
        res_ids.difference_update(records._ids)
        _debug.perf.count(
            "comodel_access_checked",
            model=res_model,
            operation=operation,
            inaccessible=len(res_ids),
        )
        for res_id in res_ids:
            yield res_model, res_id
