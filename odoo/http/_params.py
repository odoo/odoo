from __future__ import annotations

import annotationlib
import dataclasses
import enum
import functools
import inspect
import logging
import math
import re
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


class Range(NamedTuple):
    ge: float | None = None
    le: float | None = None


class Pattern(NamedTuple):
    regex: str


class Discriminator(NamedTuple):
    field: str


class Constraints(NamedTuple):
    choices: tuple[Any, ...] | None = None
    ge: float | None = None
    le: float | None = None
    pattern: str | None = None


class ParamSpec(NamedTuple):
    target: type
    item: type | None
    allow_none: bool
    required: bool
    fields: dict[str, ParamSpec] | None = None
    item_fields: dict[str, ParamSpec] | None = None
    constraints: Constraints | None = None
    discriminator: str | None = None
    variants: dict[Any, ParamSpec] | None = None


def _is_enum(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, enum.Enum)


def _get_choices_spec(
    annotation: Any, allow_none: bool, required: bool
) -> ParamSpec | None:
    if typing.get_origin(annotation) is typing.Literal:
        choices = typing.get_args(annotation)
        target: Any = str
    elif _is_enum(annotation):
        choices = tuple(member.value for member in annotation)
        target = annotation
    else:
        return None
    value_types = {type(choice) for choice in choices}
    if len(value_types) != 1 or value_types & {bool} or not value_types <= _PRIMITIVES:
        return None
    if target is str:
        target = value_types.pop()
    return ParamSpec(
        target, None, allow_none, required, constraints=Constraints(choices=choices)
    )


@functools.cache
def _compile_pattern(pattern: str) -> re.Pattern[str]:
    # Keyed by the patterns route annotations declare, never by request data.
    return re.compile(pattern)


def _split_annotated(
    annotation: Any,
) -> tuple[Any, Constraints | None, str | None]:
    if typing.get_origin(annotation) is not typing.Annotated:
        return annotation, None, None
    base, *metadata = typing.get_args(annotation)
    ge = le = None
    pattern = None
    discriminator = None
    for marker in metadata:
        if isinstance(marker, Range):
            ge = marker.ge if marker.ge is not None else ge
            le = marker.le if marker.le is not None else le
        elif isinstance(marker, Pattern):
            _compile_pattern(marker.regex)
            pattern = marker.regex
        elif isinstance(marker, Discriminator):
            discriminator = marker.field
    if ge is None and le is None and pattern is None:
        return base, None, discriminator
    return base, Constraints(ge=ge, le=le, pattern=pattern), discriminator


def _get_union_spec(
    annotation: Any, discriminator: str, required: bool, seen: frozenset[type]
) -> ParamSpec | None:
    members = list(typing.get_args(annotation))
    allow_none = type(None) in members
    members = [member for member in members if member is not type(None)]
    if len(members) < 2:
        return None
    variants: dict[Any, ParamSpec] = {}
    for member in members:
        spec = _get_spec(member, True, seen)
        if spec is None or spec.fields is None:
            _debug.logic(
                "http.params.union_declined",
                reason="member_not_object",
                field=discriminator,
            )
            return None
        tag_spec = spec.fields.get(discriminator)
        choices = (
            tag_spec.constraints.choices if tag_spec and tag_spec.constraints else None
        )
        if not choices or len(choices) != 1 or choices[0] in variants:
            _debug.logic(
                "http.params.union_declined",
                reason="tag_not_unique",
                field=discriminator,
            )
            return None
        variants[choices[0]] = spec
    return ParamSpec(
        dict, None, allow_none, required, discriminator=discriminator, variants=variants
    )


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    if isinstance(annotation, types.UnionType):
        args = typing.get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0], type(None) in args
    return annotation, False


def _get_object_members(cls: Any) -> list[tuple[str, Any, bool]] | None:
    if not isinstance(cls, type):
        return None
    try:
        hints = typing.get_type_hints(cls, include_extras=True)
    except Exception:
        _debug.logic("http.params.object_unresolved", cls=cls.__qualname__)
        return None
    if dataclasses.is_dataclass(cls):
        if any(isinstance(hint, dataclasses.InitVar) for hint in hints.values()):
            _debug.logic("http.params.object_unresolved", cls=cls.__qualname__)
            return None
        return [
            (
                field.name,
                hints.get(field.name, field.type),
                field.default is dataclasses.MISSING
                and field.default_factory is dataclasses.MISSING,
            )
            for field in dataclasses.fields(cls)
            if field.init
        ]
    if typing.is_typeddict(cls):
        required_keys: frozenset[str] = getattr(cls, "__required_keys__", frozenset())
        return [
            (name, _strip_typeddict_qualifiers(hint), name in required_keys)
            for name, hint in hints.items()
        ]
    return None


_TYPEDDICT_QUALIFIERS = (typing.Required, typing.NotRequired, typing.ReadOnly)


def _strip_typeddict_qualifiers(hint: Any) -> Any:
    while typing.get_origin(hint) in _TYPEDDICT_QUALIFIERS:
        (hint,) = typing.get_args(hint)
    return hint


def _get_dataclass_fields(
    cls: Any, seen: frozenset[type]
) -> dict[str, ParamSpec] | None:
    if cls in seen:
        return None
    members = _get_object_members(cls)
    if members is None:
        return None
    fields: dict[str, ParamSpec] = {}
    for name, hint, required in members:
        spec = _get_spec(hint, required, seen | {cls})
        if spec is None:
            _debug.logic(
                "http.params.object_uncoerced", cls=cls.__qualname__, field=name
            )
            return None
        fields[name] = spec
    return fields


def _get_spec(
    annotation: Any, required: bool, seen: frozenset[type] = frozenset()
) -> ParamSpec | None:
    unwrapped, optional = _unwrap_optional(annotation)
    inner, constraints, discriminator = _split_annotated(unwrapped)
    if discriminator is not None:
        union = _get_union_spec(inner, discriminator, required, seen)
        return (
            None
            if union is None
            else union._replace(allow_none=union.allow_none or optional)
        )
    if optional or inner is not unwrapped:
        base = _get_spec(inner, required, seen)
        if base is None:
            return None
        if constraints is not None and (base.fields is not None or base.target is list):
            _debug.logic(
                "http.params.constraints_declined",
                target=getattr(base.target, "__qualname__", str(base.target)),
            )
            return None
        if constraints is not None and not _is_orderable(base, constraints):
            target = getattr(base.target, "__qualname__", str(base.target))
            raise TypeError(f"Range bounds a number, not {target}")
        merged = constraints
        if base.constraints is not None:
            merged = Constraints(
                choices=base.constraints.choices,
                ge=constraints.ge if constraints else None,
                le=constraints.le if constraints else None,
                pattern=constraints.pattern if constraints else None,
            )
        return base._replace(allow_none=base.allow_none or optional, constraints=merged)
    choices_spec = _get_choices_spec(inner, False, required)
    if choices_spec is not None:
        return choices_spec
    target, item = _get_primitive_target(inner)
    if target is list and item is None:
        args = typing.get_args(inner)
        if args and _get_object_members(args[0]) is not None:
            item_fields = _get_dataclass_fields(args[0], seen)
            if item_fields is None:
                return None
            return ParamSpec(list, args[0], False, required, None, item_fields)
    if target is not None:
        return ParamSpec(target, item, False, required)
    fields = _get_dataclass_fields(inner, seen)
    if fields is None:
        return None
    return ParamSpec(inner, None, False, required, fields, None)


def _is_orderable(base: ParamSpec, constraints: Constraints) -> bool:
    if constraints.ge is None and constraints.le is None:
        return True
    values = (base.constraints.choices if base.constraints else None) or ()
    return base.target in (int, float) or (
        bool(values)
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values)
    )


def _get_primitive_target(annotation: Any) -> tuple[type | None, type | None]:
    if annotation is list:
        return list, None
    if typing.get_origin(annotation) is list:
        item_args = typing.get_args(annotation)
        item = item_args[0] if item_args else None
        return list, item if item in _PRIMITIVES else None
    if annotation in _PRIMITIVES:
        return annotation, None
    return None, None


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
        spec = _get_spec(annotation, param.default is inspect.Parameter.empty)
        if spec is None:
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
        specs[param.name] = spec
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
    if isinstance(value, int) and value in (0, 1):
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


def _coerce_object(name: str, value: Any, spec: ParamSpec) -> Any:
    fields = spec.fields or {}
    if not isinstance(value, dict):
        raise ParameterError(f"parameter {name!r} must be an object")
    unknown = sorted(value.keys() - fields.keys())
    if unknown:
        raise ParameterError(f"parameter {name!r} has unknown field(s) {unknown}")
    coerced: dict[str, Any] = {}
    for field_name, field_spec in fields.items():
        if field_name not in value:
            if field_spec.required:
                raise ParameterError(
                    f"parameter {name!r} is missing required field {field_name!r}"
                )
            continue
        coerced[field_name] = _coerce_value(
            f"{name}.{field_name}", value[field_name], field_spec
        )
    try:
        return spec.target(**coerced)
    except (TypeError, ValueError) as exc:
        raise ParameterError(f"parameter {name!r} is invalid: {exc}") from exc


def _is_blankable(spec: ParamSpec) -> bool:
    return (
        spec.fields is None
        and spec.variants is None
        and spec.target not in (str, bool, list)
        and not (
            spec.constraints is not None
            and spec.constraints.choices is not None
            and "" in spec.constraints.choices
        )
    )


def _check_constraints(name: str, value: Any, constraints: Constraints) -> None:
    if constraints.choices is not None and value not in constraints.choices:
        raise ParameterError(
            f"parameter {name!r} must be one of {list(constraints.choices)}"
        )
    if constraints.ge is not None and value < constraints.ge:
        raise ParameterError(f"parameter {name!r} must be >= {constraints.ge}")
    if constraints.le is not None and value > constraints.le:
        raise ParameterError(f"parameter {name!r} must be <= {constraints.le}")
    if constraints.pattern is not None and not _compile_pattern(
        constraints.pattern
    ).fullmatch(str(value)):
        raise ParameterError(f"parameter {name!r} must match {constraints.pattern!r}")


def _coerce_constrained_scalar(name: str, value: Any, spec: ParamSpec) -> Any:
    target = spec.target
    if _is_enum(target):
        if spec.constraints is None or not spec.constraints.choices:
            raise RuntimeError("enum coercion needs the spec's declared choices")
        raw = _coerce_scalar(name, value, type(spec.constraints.choices[0]))
        _check_constraints(name, raw, spec.constraints)
        return target(raw)
    coerced = _coerce_scalar(name, value, target)
    if spec.constraints is not None:
        _check_constraints(name, coerced, spec.constraints)
    return coerced


def _coerce_union(name: str, value: Any, spec: ParamSpec) -> Any:
    variants = spec.variants or {}
    if not isinstance(value, dict):
        raise ParameterError(f"parameter {name!r} must be an object")
    if spec.discriminator not in value:
        raise ParameterError(
            f"parameter {name!r} must carry {spec.discriminator!r} to say which "
            f"of {sorted(map(str, variants))} it is"
        )
    tag = value[spec.discriminator]
    variant = variants.get(tag) if type(tag) in (str, int, float) else None
    if variant is None:
        raise ParameterError(
            f"parameter {name!r}: {spec.discriminator!r} must be one of "
            f"{sorted(map(str, variants))}"
        )
    _debug.logic(
        "http.params.union_variant",
        param=name,
        tag=tag,
        target=getattr(variant.target, "__qualname__", str(variant.target)),
    )
    return _coerce_object(name, value, variant)


def _coerce_value(name: str, value: Any, spec: ParamSpec) -> Any:
    if value == "" and spec.allow_none and _is_blankable(spec):
        # An empty form input: "no value", not a malformed number.
        return None
    if value is None:
        if spec.allow_none:
            return None
        raise ParameterError(f"parameter {name!r} must not be null")
    if spec.fields is not None:
        return _coerce_object(name, value, spec)
    if spec.variants is not None:
        return _coerce_union(name, value, spec)
    if spec.constraints is not None:
        return _coerce_constrained_scalar(name, value, spec)
    if spec.target is list:
        items = value if isinstance(value, (list, tuple)) else [value]
        if spec.item_fields is not None and spec.item is not None:
            item_spec = ParamSpec(spec.item, None, False, True, spec.item_fields)
            return [
                _coerce_object(f"{name}[{i}]", item, item_spec)
                for i, item in enumerate(items)
            ]
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
                object=spec.fields is not None or spec.item_fields is not None,
            )
            raise
    _debug.pipeline(
        "http.params.coerced",
        specs=len(specs),
        present=sum(1 for name in specs if name in params),
    )
    return coerced
