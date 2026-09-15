import datetime
import decimal
import logging
import typing
from collections.abc import (
    Callable,
    Iterable,
    Iterator,
    Mapping,
    MutableSequence,
    Sequence,
)
from collections.abc import Set as AbstractSet
from contextlib import suppress

import psycopg

from odoo import api
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    UserError,
)
from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import current_worker_thread
from odoo.models import BaseModel
from odoo.modules.registry import Registry
from odoo.tools import lazy
from odoo.tools.safe_eval import _UNSAFE_ATTRIBUTES

from ._dispatch import is_db_rpc_exposed
from .transaction import (
    PG_CONCURRENCY_ERRORS_TO_RETRY,
    PG_CONCURRENCY_EXCEPTIONS_TO_RETRY,
    retrying,
)

if typing.TYPE_CHECKING:
    from odoo.db import BaseCursor

    from .transaction import RetryParticipant

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class Params:
    def __init__(self, args: Sequence, kwargs: dict) -> None:
        self.args = args
        self.kwargs = kwargs

    def __str__(self) -> str:
        params = [repr(arg) for arg in self.args]
        params.extend(f"{key}={value!r}" for key, value in sorted(self.kwargs.items()))
        return ", ".join(params)


def get_public_method(model: BaseModel, name: str) -> Callable:
    assert isinstance(model, BaseModel)
    if not isinstance(name, str):
        raise AttributeError(
            f"The method {name!r} does not exist on model '{model._name}'"
        )
    if name.startswith("_") or name in _UNSAFE_ATTRIBUTES:
        _debug.logic(
            "rpc.method_refused", model=model._name, method=name, reason="private"
        )
        raise AccessError(  # noqa: E8505  rejection reply to a bad RPC call
            f"Private methods (such as '{model._name}.{name}') "
            f"cannot be called remotely."
        )

    cls = type(model)
    # Once private, private in every override: an override that drops
    # @api.private must not reopen the method, so the whole MRO is read, and
    # through __dict__ so the caller's name runs no descriptor before that.
    for mro_cls in cls.__mro__:
        if getattr(mro_cls.__dict__.get(name), "_api_private", False):
            _debug.logic(
                "rpc.method_refused",
                model=model._name,
                method=name,
                reason="api_private",
                declared_in=mro_cls.__name__,
            )
            raise AccessError(  # noqa: E8505  rejection reply to a bad RPC call
                f"Private methods (such as '{model._name}.{name}') "
                f"cannot be called remotely."
            )

    method = getattr(cls, name, None)
    if not callable(method):
        _debug.logic("rpc.method_missing", model=model._name, method=name)
        error = AttributeError(f"The method '{model._name}.{name}' does not exist")
        error.loglevel = logging.WARNING  # type: ignore[attr-defined]
        raise error

    if method == getattr(model, name, None):
        _debug.logic(
            "rpc.method_refused", model=model._name, method=name, reason="not_bound"
        )
        raise AccessError(  # noqa: E8505  rejection reply to a bad RPC call
            f"The method '{model._name}.{name}' cannot be called remotely."
        )

    _debug.perf.count("rpc.public_method_resolved", model=model._name, method=name)
    return method


def call_kw(model: BaseModel, name: str, args: Sequence, kwargs: Mapping) -> typing.Any:
    method = get_public_method(model, name)
    api_model = getattr(method, "_api_model", False)

    create_vals = None

    if name == "create":
        if not args:
            _debug.logic("rpc.call_kw.rejected", model=model._name, reason="no_vals")
            raise AccessError(  # noqa: E8505  names the caller's own protocol error
                f"Method '{model._name}.create' requires a vals dict or list "
                f"of vals dicts as its first positional argument."
            )
        if not api_model:
            _debug.logic(
                "rpc.call_kw.rejected", model=model._name, reason="create_not_model"
            )
            raise AccessError(  # noqa: E8505  addresses whoever wrote the override
                f"Method '{model._name}.create' is not declared with "
                f"@api.model_create_multi (or @api.model). An override that "
                f"drops the decorator makes call_kw treat the vals as record "
                f"ids."
            )
        create_vals = args[0]

    if api_model:
        recs = model
    else:
        if not args:
            _debug.logic(
                "rpc.call_kw.rejected", model=model._name, method=name, reason="no_ids"
            )
            raise AccessError(  # noqa: E8505  names the caller's own protocol error
                f"Method '{model._name}.{name}' requires record ids as its "
                f"first positional argument."
            )
        ids, args = args[0], args[1:]
        recs = model.browse(ids)

    kwargs = dict(kwargs)
    context = kwargs.pop("context", None) or {}
    recs = recs.with_context(context)

    _logger.debug("call %s.%s(%s)", recs, method.__name__, Params(args, kwargs))
    with _debug.perf(
        "rpc.call_kw",
        cr=recs.env.cr,
        model=recs._name,
        method=name,
        records=len(recs),
        api_model=api_model,
        context_keys=len(context),
    ):
        result = method(recs, *args, **kwargs)

    if name == "create":
        result = result.id if isinstance(create_vals, Mapping) else result.ids
        _debug.pipeline(
            "rpc.call_kw.result",
            model=recs._name,
            method=name,
            kind="id" if isinstance(create_vals, Mapping) else "ids",
        )
    elif isinstance(result, BaseModel):
        _debug.pipeline(
            "rpc.call_kw.result",
            model=recs._name,
            method=name,
            kind="ids",
            result_model=result._name,
            records=len(result),
        )
        result = result.ids

    return result


def dispatch(dispatch_method: str, params: Sequence) -> typing.Any:
    if dispatch_method not in ("execute", "execute_kw"):
        _debug.logic(
            "rpc.dispatch.refused", reason="unknown_method", method=dispatch_method
        )
        raise AttributeError(f"Method not found: {dispatch_method}")
    if len(params) < 5:
        _debug.logic(
            "rpc.dispatch.refused",
            reason="arity",
            method=dispatch_method,
            params=len(params),
        )
        raise TypeError(
            f"{dispatch_method} requires at least 5 positional arguments "
            f"(db, uid, passwd, model, method); got {len(params)}."
        )
    db, uid, passwd, model, model_method, *args = params
    if not isinstance(uid, int) or isinstance(uid, bool):
        _debug.logic("rpc.dispatch.refused", reason="uid_type", db=db)
        raise TypeError(f"uid must be an integer (got {uid!r})")
    if not passwd:
        _debug.logic("rpc.dispatch.refused", reason="empty_password", db=db, uid=uid)
        raise AccessDenied
    if not is_db_rpc_exposed(db):
        _logger.warning(
            "RPC %s refused: database %r is not exposed by this instance",
            dispatch_method,
            db,
        )
        _debug.logic("rpc.dispatch.refused", db=db, reason="db_not_exposed")
        raise AccessDenied

    thread = current_worker_thread()
    thread.dbname = db
    thread.uid = uid
    _debug.pipeline(
        "rpc.dispatch",
        method=dispatch_method,
        db=db,
        uid=uid,
        model=model,
        model_method=model_method,
    )
    try:
        registry = Registry(db).check_signaling()
    except psycopg.errors.InvalidCatalogName as exc:
        _logger.debug("RPC %s: database %r does not exist", dispatch_method, db)
        _debug.logic("rpc.dispatch.refused", db=db, reason="db_missing")
        raise AccessDenied from exc
    try:
        if dispatch_method == "execute":
            kw = {}
        else:
            if len(args) == 1:
                args.append({})
            elif len(args) != 2:
                _debug.logic(
                    "rpc.dispatch.refused",
                    reason="execute_kw_shape",
                    db=db,
                    model=model,
                    extra_args=len(args),
                )
                raise TypeError(
                    f"execute_kw requires (args, [kw]) after the credentials "
                    f"and model.method; got {len(args)} extra arguments."
                )
            args, kw = args
            if kw is None:
                kw = {}
        with registry.cursor() as cr:
            with _debug.perf("rpc.dispatch.password_checked", cr=cr, db=db, uid=uid):
                api.Environment(cr, api.SUPERUSER_ID, {})[
                    "res.users"
                ]._check_uid_passwd(uid, passwd)
            res = execute_cr(cr, uid, model, model_method, args, kw)
    except Exception:
        _debug.logic("rpc.dispatch.failed", db=db, model=model, method=model_method)
        with suppress(Exception):
            registry.reset_changes()
        raise
    return res


def execute_cr(
    cr: BaseCursor,
    uid: int,
    obj: str,
    method: str,
    args: list | tuple,
    kw: dict,
    participant: RetryParticipant | None = None,
) -> typing.Any:
    cr.reset()
    env = api.Environment(cr, uid, {})
    env.transaction.default_env = env
    recs = env.get(obj)
    if recs is None:
        _debug.logic("rpc.execute_cr.model_missing", model=obj, method=method)
        raise UserError(  # noqa: E8505  the RPC named a model that does not exist
            f"Object {obj} doesn't exist"
        )
    thread = current_worker_thread()
    thread.rpc_model_method = f"{obj}.{method}"
    _debug.pipeline("rpc.execute_cr", model=obj, method=method, uid=uid)

    def invoke():
        # Deferred model work belongs to the attempt, before flush and commit.
        return _force_lazy_values(call_kw(recs, method, args, kw))

    result = retrying(invoke, env, participant)
    if result is None:
        _logger.debug("The method %s of the object %s returned `None`.", method, obj)
        _debug.logic("rpc.result_none", model=obj, method=method)
    return result


def _force_lazy_values(result: typing.Any) -> typing.Any:
    memo: _LazyMemo = {}
    try:
        with _debug.perf("rpc.lazy_values_forced") as span:
            forced = _force_lazy_in_value(result, memo, set())
            span.set(nodes=len(memo))
        return forced
    except RecursionError as exc:
        _debug.logic("rpc.result_rejected", reason="recursion", nodes=len(memo))
        raise ValueError("RPC result is cyclic or nested too deeply") from exc


_SCALAR_LEAF_TYPES = frozenset(
    {
        int,
        float,
        bool,
        str,
        bytes,
        type(None),
        datetime.date,
        datetime.datetime,
        datetime.time,
        datetime.timedelta,
        decimal.Decimal,
    }
)
_LazyMemo = dict[int, tuple[object, typing.Any]]


def _is_bare_iterator(val: typing.Any) -> bool:
    return not isinstance(val, lazy) and isinstance(val, Iterator)


def _force_lazy_in_mapping(val: Mapping, memo: _LazyMemo, active: set[int]) -> Mapping:
    # Mapping ABCs do not establish writability: frozendict inherits dict but
    # rejects assignment. Replacements go in a wire-compatible copy, made only
    # once a value has actually been replaced. The keys are snapshotted because
    # a lazy may write back into its own container when it is warmed, and a
    # registered Mapping need not offer items().
    items: dict | None = None
    keys = list(val)
    for key in keys:
        value = val[key]
        if value.__class__ in _SCALAR_LEAF_TYPES:
            continue
        forced = _force_lazy_in_value(value, memo, active)
        if forced is not value:
            if items is None:
                items = {k: val[k] for k in keys}
            items[key] = forced
    return val if items is None else items


def _force_lazy_in_sequence(
    val: Sequence, memo: _LazyMemo, active: set[int]
) -> Sequence:
    if isinstance(val, MutableSequence):
        for index, item in enumerate(val):
            if item.__class__ not in _SCALAR_LEAF_TYPES:
                forced = _force_lazy_in_value(item, memo, active)
                if forced is not item:
                    val[index] = forced
        return val
    items: list | None = None
    for index, item in enumerate(val):
        if item.__class__ in _SCALAR_LEAF_TYPES:
            continue
        forced = _force_lazy_in_value(item, memo, active)
        if forced is not item:
            if items is None:
                items = list(val)
            items[index] = forced
    if items is None:
        return val
    return tuple(items) if type(val) is tuple else type(val)(items)  # type: ignore[call-arg]


def _force_lazy_in_place(val: Iterable, memo: _LazyMemo, active: set[int]) -> None:
    for item in val:
        if item.__class__ not in _SCALAR_LEAF_TYPES and not _is_bare_iterator(item):
            _force_lazy_in_value(item, memo, active)


def _force_lazy_in_value(
    val: typing.Any, memo: _LazyMemo, active: set[int]
) -> typing.Any:
    cls = val.__class__
    if cls in _SCALAR_LEAF_TYPES:
        return val
    marker = id(val)
    cached = memo.get(marker)
    if cached is not None:
        return cached[1]
    if marker in active:
        _debug.logic("rpc.result_rejected", reason="cyclic", type=type(val).__name__)
        raise ValueError("RPC result is cyclic")
    active.add(marker)
    try:
        result = val
        # Exact types first: the ABC checks below cost a metaclass call each,
        # and a search_read result is dicts of lists of tuples all the way down.
        if cls is dict:
            result = _force_lazy_in_mapping(val, memo, active)
        elif cls is list or cls is tuple:
            result = _force_lazy_in_sequence(val, memo, active)
        elif isinstance(val, lazy):
            value = val._value
            forced = _force_lazy_in_value(value, memo, active)
            result = val if forced is value else forced
        elif isinstance(val, (str, bytes, BaseModel)):
            pass
        elif isinstance(val, Mapping):
            result = _force_lazy_in_mapping(val, memo, active)
        elif isinstance(val, Iterator):
            result = [_force_lazy_in_value(item, memo, active) for item in val]
        elif isinstance(val, Sequence):
            result = _force_lazy_in_sequence(val, memo, active)
        elif isinstance(val, (AbstractSet, Iterable)):
            _force_lazy_in_place(val, memo, active)
        # Retain the input too: temporary values yielded by generators may
        # otherwise be destroyed and have their identities reused mid-walk.
        memo[marker] = (val, result)
        return result
    finally:
        active.remove(marker)


__all__ = (
    "PG_CONCURRENCY_ERRORS_TO_RETRY",
    "PG_CONCURRENCY_EXCEPTIONS_TO_RETRY",
    "Params",
    "call_kw",
    "dispatch",
    "execute_cr",
    "get_public_method",
)
