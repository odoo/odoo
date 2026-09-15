from __future__ import annotations

import annotationlib
import inspect
import logging
import math
import types
import typing
from typing import Any, NamedTuple

from odoo.libs.debug_log import DebugLog

from .exceptions import ParameterError

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_PRIMITIVES: frozenset[type] = frozenset({int, float, bool, str})

_TRUE_TOKENS: frozenset[str] = frozenset({"true", "1", "on", "yes", "t"})
_FALSE_TOKENS: frozenset[str] = frozenset({"false", "0", "off", "no", "f", ""})


class ParamSpec(NamedTuple):
    target: type
    item: type | None
    allow_none: bool
    required: bool


def _get_param_spec_fields(
    annotation: Any,
) -> tuple[type | None, type | None, bool]:
    allow_none = False
    if isinstance(annotation, types.UnionType):
        args = typing.get_args(annotation)
        allow_none = type(None) in args
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) != 1:
            return None, None, allow_none
        annotation = non_none[0]

    origin = typing.get_origin(annotation)
    if annotation is list:
        return list, None, allow_none
    if origin is list:
        item_args = typing.get_args(annotation)
        item = item_args[0] if item_args else None
        if item not in _PRIMITIVES:
            item = None
        return list, item, allow_none
    if annotation in _PRIMITIVES:
        return annotation, None, allow_none
    return None, None, allow_none


def get_param_specs(
    endpoint: typing.Callable, inherited: dict[str, ParamSpec] | None = None
) -> dict[str, ParamSpec]:
    specs: dict[str, ParamSpec] = dict(inherited or {})
    params = list(
        inspect.signature(
            endpoint, annotation_format=annotationlib.Format.FORWARDREF
        ).parameters.values()
    )
    if not any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params):
        accepted = {
            p.name
            for p in params[1:]
            if p.kind
            in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        }
        specs = {name: spec for name, spec in specs.items() if name in accepted}
    for param in params[1:]:
        if param.kind not in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            continue
        if param.annotation is inspect.Parameter.empty:
            if param.name in specs:
                specs[param.name] = specs[param.name]._replace(
                    required=param.default is inspect.Parameter.empty
                )
            continue
        specs.pop(param.name, None)
        annotation = param.annotation
        if isinstance(annotation, str):
            try:
                annotation = eval(annotation, getattr(endpoint, "__globals__", None))  # noqa: S307  resolves a stringified forward-ref annotation against the endpoint's own module globals; only ever fed types the addon author wrote on their own route signature, never request-supplied data
            except Exception:
                _logger.debug(
                    "%s: cannot resolve annotation %r for %r; parameter left uncoerced",
                    endpoint,
                    annotation,
                    param.name,
                )
                _debug.logic(
                    "http.params.uncoerced", reason="unresolved", param=param.name
                )
                continue
        target, item, allow_none = _get_param_spec_fields(annotation)
        if target is None:
            _logger.debug(
                "%s: %r is annotated %r, which typed routes do not coerce; "
                "the parameter is passed through and its absence is not caught",
                endpoint,
                param.name,
                annotation,
            )
            _debug.logic(
                "http.params.uncoerced", reason="unsupported_type", param=param.name
            )
            continue
        specs[param.name] = ParamSpec(
            target=target,
            item=item,
            allow_none=allow_none,
            required=param.default is inspect.Parameter.empty,
        )
    _debug.pipeline(
        "http.params.specs",
        endpoint=getattr(endpoint, "__qualname__", None),
        specs=len(specs),
        inherited=len(inherited or ()),
        required=sum(1 for spec in specs.values() if spec.required),
    )
    return specs


def _coerce_bool(name: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        token = value.strip().lower()
        if token in _TRUE_TOKENS:
            return True
        if token in _FALSE_TOKENS:
            return False
    if isinstance(value, int):
        return bool(value)
    raise ParameterError(f"parameter {name!r} must be a boolean")


def _check_json_number_syntax(name: str, value: Any, kind: str) -> None:
    if isinstance(value, str) and ("_" in value or not value.isascii()):
        raise ParameterError(f"parameter {name!r} must be {kind}")


def _coerce_scalar(name: str, value: Any, target: type) -> Any:
    if target is str:
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            raise ParameterError(f"parameter {name!r} must be a string")
        if isinstance(value, (int, float)):
            return str(value)
        raise ParameterError(f"parameter {name!r} must be a string")
    if target is bool:
        return _coerce_bool(name, value)
    if target is int:
        if isinstance(value, bool):
            raise ParameterError(f"parameter {name!r} must be an integer")
        if isinstance(value, float) and not value.is_integer():
            raise ParameterError(f"parameter {name!r} must be an integer")
        _check_json_number_syntax(name, value, "an integer")
        try:
            return int(value)
        except TypeError, ValueError:
            raise ParameterError(f"parameter {name!r} must be an integer") from None
    if target is float:
        if isinstance(value, bool):
            raise ParameterError(f"parameter {name!r} must be a number")
        _check_json_number_syntax(name, value, "a number")
        try:
            result = float(value)
        except OverflowError:
            raise ParameterError(
                f"parameter {name!r} must be a finite number"
            ) from None
        except TypeError, ValueError:
            raise ParameterError(f"parameter {name!r} must be a number") from None
        if not math.isfinite(result):
            raise ParameterError(f"parameter {name!r} must be a finite number")
        return result
    return value


def _coerce_value(name: str, value: Any, spec: ParamSpec) -> Any:
    if value is None:
        if spec.allow_none:
            return None
        raise ParameterError(f"parameter {name!r} must not be null")
    if spec.target is list:
        items = value if isinstance(value, (list, tuple)) else [value]
        if spec.item is None:
            return list(items)
        return [_coerce_scalar(name, item, spec.item) for item in items]
    return _coerce_scalar(name, value, spec.target)


def coerce_params(
    params: dict[str, Any], specs: dict[str, ParamSpec]
) -> dict[str, Any]:
    if not specs:
        return params
    coerced = dict(params)
    for name, spec in specs.items():
        if name not in params:
            if spec.required:
                _debug.logic("http.params.missing_required", param=name)
                raise ParameterError(f"missing required parameter {name!r}")
            continue
        try:
            coerced[name] = _coerce_value(name, params[name], spec)
        except ParameterError:
            _debug.logic(
                "http.params.rejected",
                param=name,
                target=spec.target.__name__,
                item=None if spec.item is None else spec.item.__name__,
                got=type(params[name]).__name__,
            )
            raise
    _debug.pipeline(
        "http.params.coerced",
        specs=len(specs),
        present=sum(1 for name in specs if name in params),
    )
    return coerced
