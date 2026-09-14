import itertools
import logging
import typing
from collections.abc import Callable, Collection, Iterable, Iterator

from odoo.exceptions import AccessError, MissingError
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import _OrmProfile

from .._recordset import is_recordset
from ..primitives import PREFETCH_MAX

if typing.TYPE_CHECKING:
    from .._typing import ModelLike
    from ..primitives import IdType
    from .base import Field

_orm_compute = logging.getLogger("odoo.orm.compute")
_debug = DebugLog(__name__)


def call_hook(
    needle: str | Callable[..., typing.Any] | None,
    records: ModelLike,
    *args: object,
) -> typing.Any:
    if not is_recordset(records):
        msg = "Hook dispatch requires a subject recordset"
        raise TypeError(msg)
    if isinstance(needle, str):
        method = getattr(records, needle)
        call_args: tuple = args
    elif callable(needle):
        method = needle
        call_args = (records, *args)
    else:
        msg = "Hook dispatch requires a callable or method name"
        raise TypeError(msg)

    name = getattr(method, "__name__", "")
    if name.startswith("__"):
        msg = (
            f"Hook dispatch refuses {name!r}: a dunder cannot be a compute, "
            f"inverse, search or group_expand target"
        )
        raise TypeError(msg)
    return method(*call_args)


def _expand_ids(id0: IdType, ids: Iterable[IdType]) -> Iterator[IdType]:
    yield id0
    seen = {id0}
    kind = bool(id0)
    for id_ in ids:
        if id_ not in seen and bool(id_) == kind:
            yield id_
            seen.add(id_)


def recompute(field: Field, records: ModelLike) -> None:
    to_compute_ids = records.env.core.get_pending_ids(field)
    if not to_compute_ids:
        return

    prof = _OrmProfile(_orm_compute)
    if prof.debug:
        _pending_before = len(to_compute_ids)

        def _count():
            remaining = records.env.core.get_pending_ids(field)
            return _pending_before - len(remaining or ())

    def apply_except_missing(func, records):
        try:
            func(records)
            return
        except MissingError:
            pass

        existing = records.exists()
        missing = records - existing
        _debug.logic(
            "field.recompute.missing_records",
            model=field.model_name,
            field=field.name,
            records=len(records),
            missing=len(missing),
        )
        if existing:
            func(existing)
        # a record that is gone is gone for every pending field of the model,
        # not only this one: the next field's recompute would only find it
        # missing again, one existence query each
        for f in records._get_stored_computed_fields():
            records.env.remove_to_compute(f, missing)

    if field.recursive:
        _recompute_singly(field, records, to_compute_ids, apply_except_missing)
    else:
        _recompute_batched(field, records, to_compute_ids, apply_except_missing)

    prof.stop()
    prof.report(
        _orm_compute,
        "recompute %s.%s: %d records (recursive=%s)",
        field.model_name,
        field.name,
        _count() if prof.debug else 0,
        field.recursive,
    )


def _recompute_singly(
    field: Field,
    records: ModelLike,
    to_compute_ids: Collection[IdType],
    apply_except_missing: Callable,
) -> None:
    computed_ids: list = []

    def recursive_compute(records):
        for record in records:
            if record.id in to_compute_ids:
                field.compute_value(record, validate=False)
                computed_ids.append(record.id)

    record_ids = records._ids
    expanded = (
        len(record_ids) == 1
        and record_ids[0] in to_compute_ids
        and not records.env.core.has_any_protected()
    )
    if expanded:
        records = records.browse(
            itertools.islice(_expand_ids(record_ids[0], to_compute_ids), PREFETCH_MAX)
        )
        _debug.logic(
            "field.recompute.recursive_expanded",
            model=field.model_name,
            field=field.name,
            pending=len(to_compute_ids),
            batch=len(records),
        )

    try:
        apply_except_missing(recursive_compute, records)
    except AccessError:
        if not (expanded and record_ids[0] in computed_ids):
            raise
        _debug.logic(
            "field.recompute.recursive_access_error_swallowed",
            model=field.model_name,
            field=field.name,
            computed=len(computed_ids),
        )
    if computed_ids:
        records.browse(computed_ids)._check_computed(field)


def _recompute_batched(
    field: Field,
    records: ModelLike,
    to_compute_ids: Collection[IdType],
    apply_except_missing: Callable,
) -> None:
    for record in records:
        if record.id in to_compute_ids:
            ids = _expand_ids(record.id, to_compute_ids)
            recs = record.browse(itertools.islice(ids, PREFETCH_MAX))
            try:
                apply_except_missing(field.compute_value, recs)
                continue
            except AccessError:
                pass
            _debug.logic(
                "field.recompute.batch_access_error_single",
                model=field.model_name,
                field=field.name,
                batch=len(recs),
            )
            field.compute_value(record)


def compute_value(field: Field, records: ModelLike, validate: bool = True) -> None:
    prof = _OrmProfile(_orm_compute)

    env = records.env
    if field.compute_sudo:
        records = records.sudo()
    fields = records.pool.field_computed[field]

    for computed in fields:
        if computed.store:
            env.remove_to_compute(computed, records)

    _debug.pipeline(
        "field.compute_value",
        model=field.model_name,
        field=field.name,
        records=len(records),
        computed_together=len(fields),
        sudo=bool(field.compute_sudo),
        validate=validate,
    )
    try:
        with records.env.protecting(fields, records):
            records._compute_field_value(field, validate=validate)
    except Exception as e:
        _debug.logic(
            "field.compute.failed_rescheduled",
            model=field.model_name,
            field=field.name,
            records=len(records),
            error=type(e).__name__,
        )
        for computed in fields:
            if computed.store:
                env.add_to_compute(computed, records)
        raise

    prof.stop()
    prof.report(
        _orm_compute,
        "compute_value %s.%s: %d records (sudo=%s)",
        field.model_name,
        field.name,
        len(records),
        field.compute_sudo,
    )


def apply_inverse(field: Field, records: ModelLike) -> None:
    prof = _OrmProfile(_orm_compute)

    _debug.pipeline(
        "field.apply_inverse",
        model=field.model_name,
        field=field.name,
        records=len(records),
    )
    call_hook(field.inverse, records)

    prof.stop()
    prof.report(
        _orm_compute,
        "apply_inverse %s.%s: %d records",
        field.model_name,
        field.name,
        len(records),
    )
