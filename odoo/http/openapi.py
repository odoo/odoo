from __future__ import annotations

import annotationlib
import inspect
import logging
import re
import typing
from typing import Any, NamedTuple

from odoo.libs.debug_log import DebugLog

from ._params import ParamSpec, _get_spec, get_param_specs

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

OPENAPI_VERSION = "3.1.0"

_CONVERTER_SCHEMA: dict[str, dict[str, str]] = {
    "int": {"type": "integer"},
    "float": {"type": "number"},
}

_PRIMITIVE_SCHEMA: dict[type, dict[str, str]] = {
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    str: {"type": "string"},
}

_RULE_ARG_RE = re.compile(
    r"<(?:(?P<conv>[a-zA-Z_]\w*)(?:\([^>]*\))?:)?(?P<name>[a-zA-Z_]\w*)>"
)

_IMPLICIT_METHODS = frozenset({"HEAD", "OPTIONS"})

_DEFAULT_METHODS_JSONRPC = frozenset({"POST"})
_DEFAULT_METHODS_OTHER = frozenset({"GET", "POST"})


def _get_methods_effective(route: RouteInfo) -> frozenset[str]:
    real = route.methods - _IMPLICIT_METHODS
    if real:
        return real
    if route.routing.get("methods") is not None:
        return frozenset()
    if route.routing.get("type") == "jsonrpc":
        return _DEFAULT_METHODS_JSONRPC
    return _DEFAULT_METHODS_OTHER


_ID_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9]+")


def _prepare_operation_id(
    method: str, template: str, used: set[str] | None = None
) -> str:
    slug = _ID_SANITIZE_RE.sub("_", template).strip("_") or "root"
    base = f"{method.lower()}_{slug}"
    if used is None:
        return base
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


class RouteInfo(NamedTuple):
    rule: str
    methods: frozenset[str]
    routing: typing.Mapping[str, Any]
    handler: typing.Callable
    param_specs: dict[str, ParamSpec] | None = None


def _get_route_param_specs(route: RouteInfo) -> dict[str, ParamSpec]:
    if route.param_specs is not None:
        _debug.logic("http.openapi.param_specs", rule=route.rule, source="endpoint")
        return route.param_specs
    _debug.logic("http.openapi.param_specs", rule=route.rule, source="introspected")
    return get_param_specs(route.handler)


def _prepare_schema_nullable(schema: dict[str, Any]) -> dict[str, Any]:
    kind = schema.get("type")
    if isinstance(kind, str):
        return {**schema, "type": [kind, "null"]}
    return schema


def _prepare_object_schema(fields: dict[str, ParamSpec]) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {name: param_spec_to_schema(s) for name, s in fields.items()},
        "additionalProperties": False,
    }
    required = [name for name, s in fields.items() if s.required]
    if required:
        schema["required"] = required
    return schema


def _apply_constraints(schema: dict[str, Any], spec: ParamSpec) -> dict[str, Any]:
    constraints = spec.constraints
    if constraints is None:
        return schema
    if constraints.choices is not None:
        schema = dict(_PRIMITIVE_SCHEMA.get(type(constraints.choices[0]), {}))
        schema["enum"] = list(constraints.choices)
    if constraints.ge is not None:
        schema["minimum"] = constraints.ge
    if constraints.le is not None:
        schema["maximum"] = constraints.le
    if constraints.pattern is not None:
        schema["pattern"] = constraints.pattern
    return schema


def param_spec_to_schema(spec: ParamSpec) -> dict[str, Any]:
    if spec.variants is not None:
        one_of = [param_spec_to_schema(v) for v in spec.variants.values()]
        if spec.allow_none:
            # OpenAPI 3.1 dropped the 3.0 `nullable` keyword; null is a
            # oneOf variant (the discriminator only applies to the objects).
            one_of.append({"type": "null"})
        return {
            "oneOf": one_of,
            "discriminator": {"propertyName": spec.discriminator},
        }
    if spec.fields is not None:
        schema = _prepare_object_schema(spec.fields)
    elif spec.constraints is not None:
        schema = _apply_constraints(dict(_PRIMITIVE_SCHEMA.get(spec.target, {})), spec)
    elif spec.target is list:
        if spec.item_fields is not None:
            items: dict[str, Any] = _prepare_object_schema(spec.item_fields)
        else:
            item = _PRIMITIVE_SCHEMA.get(spec.item) if spec.item else None
            items = dict(item) if item else {}
        schema = {"type": "array", "items": items}
    else:
        schema = dict(_PRIMITIVE_SCHEMA.get(spec.target, {}))
    return _prepare_schema_nullable(schema) if spec.allow_none else schema


def get_response_schema(handler: typing.Callable) -> dict[str, Any] | None:
    try:
        annotation = inspect.signature(
            handler, annotation_format=annotationlib.Format.FORWARDREF
        ).return_annotation
    except TypeError, ValueError:
        return None
    if annotation is inspect.Signature.empty or annotation is None:
        return None
    if isinstance(annotation, str):
        try:
            annotation = eval(annotation, getattr(handler, "__globals__", None))  # noqa: S307  the route author's own return annotation, resolved against their module
        except Exception as exc:
            _debug.logic(
                "http.openapi.return_annotation_unresolved",
                handler=getattr(handler, "__qualname__", None),
                error=type(exc).__name__,
            )
            return None
    origin = typing.get_origin(annotation)
    if annotation is dict or origin is dict:
        return {"type": "object"}
    spec = _get_spec(annotation, True)
    return None if spec is None else param_spec_to_schema(spec)


def _prepare_path_template_and_params(rule: str) -> tuple[str, list[dict[str, Any]]]:
    params: list[dict[str, Any]] = []

    def replace_rule_arg_with_placeholder(match: re.Match[str]) -> str:
        name = match.group("name")
        conv = match.group("conv") or "default"
        schema = _CONVERTER_SCHEMA.get(conv, {"type": "string"})
        params.append(
            {"name": name, "in": "path", "required": True, "schema": dict(schema)}
        )
        return "{" + name + "}"

    return _RULE_ARG_RE.sub(replace_rule_arg_with_placeholder, rule), params


_SECURITY_SCHEMES: dict[str, tuple[str, dict[str, str]]] = {
    "bearer": ("bearerAuth", {"type": "http", "scheme": "bearer"}),
    "user": ("sessionCookie", {"type": "apiKey", "in": "cookie", "name": "session_id"}),
}


def _get_handler_summary(handler: typing.Callable) -> str | None:
    doc = getattr(handler, "__doc__", None)
    return doc.strip().splitlines()[0] if doc and doc.strip() else None


def _prepare_jsonrpc_envelope_schema(params_schema: dict[str, Any]) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "type": "object",
        "properties": {
            "jsonrpc": {"type": "string", "const": "2.0"},
            "method": {"type": "string"},
            "id": {"type": ["integer", "string", "null"]},
            "params": params_schema,
        },
    }
    if params_schema.get("required"):
        envelope["required"] = ["params"]
    return envelope


def prepare_openapi_operation(
    route: RouteInfo,
    method: str,
    template: str,
    path_params: list[dict[str, Any]],
    security_schemes: dict[str, dict[str, str]],
    used_operation_ids: set[str] | None = None,
) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "operationId": _prepare_operation_id(method, template, used_operation_ids),
        "responses": {"200": {"description": "Successful response"}},
    }
    if summary := _get_handler_summary(route.handler):
        operation["summary"] = summary

    parameters = list(path_params)
    route_type = route.routing.get("type", "http")
    if route.routing.get("typed"):
        path_param_names = {p["name"] for p in path_params}
        specs = {
            name: spec
            for name, spec in _get_route_param_specs(route).items()
            if name not in path_param_names
        }
        if route_type == "http":
            parameters += [
                {
                    "name": name,
                    "in": "query",
                    "required": spec.required,
                    "schema": param_spec_to_schema(spec),
                }
                for name, spec in specs.items()
            ]
        elif specs:
            required = [name for name, spec in specs.items() if spec.required]
            body: dict[str, Any] = {
                "type": "object",
                "properties": {n: param_spec_to_schema(s) for n, s in specs.items()},
            }
            if required:
                body["required"] = required
            if route_type == "jsonrpc":
                body = _prepare_jsonrpc_envelope_schema(body)
            operation["requestBody"] = {
                "content": {"application/json": {"schema": body}}
            }
        operation["responses"]["400"] = {"description": "Invalid request parameters"}

    if route_type in ("jsonrpc", "json2"):
        # A JSON route always answers JSON; without a return annotation the
        # body is any JSON value, which {} states truthfully.
        result_schema = get_response_schema(route.handler)
        if result_schema is None:
            result_schema = {}
        if route_type == "jsonrpc":
            result_schema = {
                "type": "object",
                "properties": {
                    "jsonrpc": {"type": "string", "const": "2.0"},
                    "id": {"type": ["integer", "string", "null"]},
                    "result": result_schema,
                },
            }
        operation["responses"]["200"]["content"] = {
            "application/json": {"schema": result_schema}
        }

    if parameters:
        operation["parameters"] = parameters

    auth = route.routing.get("auth")
    if auth in _SECURITY_SCHEMES:
        name, definition = _SECURITY_SCHEMES[auth]
        security_schemes[name] = definition
        operation["security"] = [{name: []}]
    elif auth in ("public", "none"):
        operation["security"] = []

    _debug.pipeline(
        "http.openapi.operation",
        id=operation["operationId"],
        method=method,
        type=route_type,
        typed=bool(route.routing.get("typed")),
        parameters=len(parameters),
        body="requestBody" in operation,
        auth=auth,
    )
    return operation


def prepare_openapi_document(
    routes: typing.Iterable[RouteInfo],
    *,
    title: str = "Odoo HTTP API",
    version: str = "19.0",
    servers: list[dict[str, Any]] | None = None,
    typed_only: bool = False,
) -> dict[str, Any]:
    paths: dict[str, dict[str, Any]] = {}
    security_schemes: dict[str, dict[str, str]] = {}
    used_operation_ids: set[str] = set()

    claimed_by: dict[tuple[str, str], str] = {}

    seen = skipped = 0  # debuglog
    with _debug.perf("http.openapi.document", typed_only=typed_only) as span:
        for route in routes:
            seen += 1  # debuglog
            if typed_only and not route.routing.get("typed"):
                skipped += 1  # debuglog
                continue
            template, path_params = _prepare_path_template_and_params(route.rule)

            repeated = {p["name"] for p in path_params}
            if len(repeated) != len(path_params):
                _logger.warning(
                    "OpenAPI: %r repeats a path parameter name and cannot be "
                    "described; werkzeug will also refuse to build a URL for it.",
                    route.rule,
                )
                _debug.logic(
                    "http.openapi.route_skipped",
                    reason="repeated_param",
                    rule=route.rule,
                )
                continue

            path_item = paths.setdefault(template, {})
            for method in sorted(_get_methods_effective(route)):
                verb = method.lower()
                if verb in path_item:
                    _logger.warning(
                        "OpenAPI: %s %s is already described by %r; %r renders to "
                        "the same path template and cannot be documented too.",
                        method,
                        template,
                        claimed_by.get((template, verb)),
                        route.rule,
                    )
                    _debug.logic(
                        "http.openapi.route_skipped",
                        reason="already_described",
                        rule=route.rule,
                        method=method,
                    )
                    continue
                claimed_by[template, verb] = route.rule
                path_item[verb] = prepare_openapi_operation(
                    route,
                    method,
                    template,
                    path_params,
                    security_schemes,
                    used_operation_ids,
                )
        span.set(
            routes=seen,
            skipped_untyped=skipped,
            paths=len(paths),
            operations=len(used_operation_ids),
            security_schemes=len(security_schemes),
        )

    document: dict[str, Any] = {
        "openapi": OPENAPI_VERSION,
        "info": {"title": title, "version": version},
        "paths": paths,
    }
    if servers:
        document["servers"] = servers
    if security_schemes:
        document["components"] = {"securitySchemes": security_schemes}
    return document


def iter_map_routes(routing_map: Any) -> typing.Iterator[RouteInfo]:
    for rule in routing_map.iter_rules():
        endpoint = rule.endpoint
        routing = getattr(endpoint, "routing", {})
        handler = getattr(endpoint, "original_endpoint", endpoint)
        yield RouteInfo(
            rule=rule.rule,
            methods=frozenset(rule.methods or ()),
            routing=routing,
            handler=handler,
            param_specs=getattr(endpoint, "_param_specs", None),
        )


def prepare_openapi_from_map(routing_map: Any, **kwargs: Any) -> dict[str, Any]:
    return prepare_openapi_document(iter_map_routes(routing_map), **kwargs)
