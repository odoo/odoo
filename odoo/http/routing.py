from __future__ import annotations

import annotationlib
import functools
import inspect
import logging
import warnings
from collections.abc import Callable, Generator, Iterable
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, NamedTuple, cast

import werkzeug.routing

from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import submap

from ._params import ParamSpec, get_param_specs
from .constants import DEFAULT_ALLOWED_METHODS, ROUTING_KEYS, SAFE_HTTP_METHODS
from .controller import Controller, _get_controllers
from .exceptions import ParameterError

if TYPE_CHECKING:
    from ._protocols import Endpoint, HasRouting, RoutedMethod
from .core import request
from .dispatcher import _dispatchers
from .wrappers import Response

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_KNOWN_ROUTING_PARAMETERS: set[str] = {
    "auth",
    "captcha",
    "cors",
    "cors_credentials",
    "cors_allow_headers",
    "cors_expose_headers",
    "csrf",
    "handle_params_access_error",
    "max_content_length",
    "readonly",
    "save_session",
    "statement_timeout",
    "type",
    "typed",
    *ROUTING_KEYS,
    "website",
    "multilang",
    "sitemap",
    "list_as_website_content",
}


def register_routing_parameters(*names: str) -> None:
    _KNOWN_ROUTING_PARAMETERS.update(names)
    _debug.lifecycle(
        "http.routing.parameters_registered",
        added=len(names),
        known=len(_KNOWN_ROUTING_PARAMETERS),
    )


class RouteDefinitionError(ValueError):
    pass


class LazyCompiledBuilder:
    def __init__(
        self,
        rule: werkzeug.routing.Rule,
        _compile_builder: Any,
        append_unknown: bool,
    ) -> None:
        self.rule = rule
        self._callable = None
        self._compile_builder = _compile_builder
        self._append_unknown = append_unknown

    def __get__(self, *args: Any) -> LazyCompiledBuilder:
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        fn = self._callable
        if fn is None:
            fn = self._compile_builder(self._append_unknown).__get__(self.rule, None)
            self._callable = fn
            _debug.lifecycle("http.rule.builder_compiled", rule=self.rule.rule)
        return fn(*args, **kwargs)


class FasterRule(werkzeug.routing.Rule):
    def _compile_builder(self, append_unknown: bool = True) -> LazyCompiledBuilder:
        return LazyCompiledBuilder(self, super()._compile_builder, append_unknown)


def prepare_rule_kwargs(endpoint: HasRouting) -> dict[str, Any]:
    routing = dict(submap(endpoint.routing, ROUTING_KEYS))
    methods = routing.get("methods")
    if methods is None:
        methods = (
            SAFE_HTTP_METHODS if routing.get("websocket") else DEFAULT_ALLOWED_METHODS
        )
    if "OPTIONS" not in methods:
        routing["methods"] = [*methods, "OPTIONS"]
    else:
        routing["methods"] = methods
    return routing


def prepare_routing_map(
    rules: Iterable[tuple[str, Endpoint]],
    converters: dict[str, type] | None = None,
) -> werkzeug.routing.Map:
    routing_map = werkzeug.routing.Map(strict_slashes=False, converters=converters)
    with _debug.perf("http.routing_map.prepare") as span:
        for url, endpoint in rules:
            rule = FasterRule(url, endpoint=endpoint, **prepare_rule_kwargs(endpoint))
            rule.merge_slashes = False
            routing_map.add(rule)
        span.set(rules=len(routing_map._rules))
    return routing_map


class _EndpointSignature(NamedTuple):
    accepts_var_keyword: bool
    accepted: frozenset[str]
    required: frozenset[str]
    bound_self_name: str


def _get_endpoint_signature(endpoint: Callable) -> _EndpointSignature:
    accepts_var_keyword = False
    named: set[str] = set()
    required: set[str] = set()
    params = list(
        inspect.signature(
            endpoint, annotation_format=annotationlib.Format.FORWARDREF
        ).parameters.values()
    )
    bound_self_name = params[0].name if params else "self"
    for param in params[1:]:
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            accepts_var_keyword = True
        elif param.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            named.add(param.name)
            if param.default is inspect.Parameter.empty:
                required.add(param.name)
    return _EndpointSignature(
        accepts_var_keyword, frozenset(named), frozenset(required), bound_self_name
    )


def _apply_param_specs(endpoint: Endpoint, specs: dict[str, Any] | None) -> None:
    endpoint._param_specs = specs
    endpoint.typed_list_params = (
        frozenset(name for name, spec in specs.items() if spec.target is list)
        if specs
        else None
    )


def _check_cors_credentials(who: str, routing: Any) -> None:
    if routing.get("cors") == "*" and routing.get("cors_credentials"):
        e = (
            f"{who}: cors='*' cannot be combined with cors_credentials. Name the "
            "allowed origin explicitly, or pass a resolver callable such as "
            "odoo.http.resolve_cors_same_host."
        )
        raise ValueError(e)


def _get_route_type_effective(declared_routing: dict[str, Any]) -> str:
    declared = declared_routing.get("type")
    if declared is not None:
        return declared
    if request:
        return request.dispatcher.routing_type
    return "http"


def route(route: str | Iterable[str] | None = None, **routing: Any) -> Callable:

    def decorator(endpoint: Callable) -> Callable:
        fname = f"<function {endpoint.__module__}.{endpoint.__name__}>"

        if routing.get("type") == "json":
            warnings.warn(
                "Since 19.0, @route(type='json') is a deprecated alias to @route(type='jsonrpc')",
                DeprecationWarning,
                stacklevel=2,
            )
            routing["type"] = "jsonrpc"
            _debug.logic("http.route.deprecated_type", endpoint=fname, declared="json")
        route_type = routing.get("type", "http")
        if route_type not in _dispatchers:
            raise ValueError(
                f"@route(type={route_type!r}) is not one of {list(_dispatchers)}"
            )
        if route:
            routing["routes"] = [route] if isinstance(route, str) else list(route)
        wrong = routing.pop("method", None)
        if wrong is not None:
            _logger.warning(
                "%s defined with invalid routing parameter 'method', assuming 'methods'",
                fname,
            )
            # Honor the "assuming" promise for the typo's most common shape,
            # a single method string, instead of raising two lines below
            # about a parameter the author never wrote.
            routing["methods"] = (wrong,) if isinstance(wrong, str) else wrong
            _debug.logic("http.route.parameter_typo", endpoint=fname, given="method")
        methods = routing.get("methods")
        if methods is not None:
            if isinstance(methods, str):
                raise ValueError(
                    "@route(methods=...) requires a collection of method names"
                )
            routing["methods"] = tuple(
                dict.fromkeys(method.upper() for method in methods)
            )
        _check_cors_credentials(fname, routing)
        unknown = routing.keys() - _KNOWN_ROUTING_PARAMETERS - {"routes"}
        if unknown:
            _logger.warning(
                "%s defined with unknown @route parameter(s) %s; they are kept "
                "in endpoint.routing, but no module declared them via "
                "odoo.http.register_routing_parameters() — possible typo.",
                fname,
                sorted(unknown),
            )
            _debug.logic(
                "http.route.unknown_parameters",
                endpoint=fname,
                unknown=",".join(sorted(unknown)),
            )

        accepts_var_keyword, accepted_params, required_params, bound_self_name = (
            _get_endpoint_signature(endpoint)
        )

        @functools.wraps(endpoint)
        def route_wrapper(controller_self, /, *args, **params):
            if not args and not params.keys() >= required_params:
                missing = sorted(required_params - params.keys())
                _debug.logic(
                    "http.route.params_missing",
                    endpoint=fname,
                    missing=",".join(missing),
                )
                raise ParameterError(f"missing required parameter(s) {missing}")
            if accepts_var_keyword:
                params_ok = params
                params_ko = None
                if bound_self_name in params:
                    params_ok = {
                        k: v for k, v in params.items() if k != bound_self_name
                    }
                    params_ko = {bound_self_name}
            elif params.keys() <= accepted_params:
                params_ok = params
                params_ko = None
            else:
                params_ok = {k: v for k, v in params.items() if k in accepted_params}
                params_ko = params.keys() - accepted_params
            if params_ko:
                _logger.warning("%s called ignoring args %s", fname, params_ko)
                _debug.logic(
                    "http.route.params_ignored",
                    endpoint=fname,
                    ignored=",".join(sorted(params_ko)),
                )

            result = endpoint(controller_self, *args, **params_ok)
            if _get_route_type_effective(routing) == "http":
                return Response.from_endpoint_result(result, fname)
            return result

        routed = cast("RoutedMethod", route_wrapper)
        routed.original_routing = routing
        routed.original_endpoint = endpoint
        _debug.lifecycle(
            "http.route.declared",
            endpoint=fname,
            type=route_type,
            routes=len(routing.get("routes", ())),
            auth=routing.get("auth"),
            typed=bool(routing.get("typed")),
        )
        return route_wrapper

    return decorator


class _ResolvedRoute(NamedTuple):
    routing: dict[str, Any]
    method: Any
    param_specs: dict[str, ParamSpec] | None


def _resolve_route(ctrl: Controller, method_name: str) -> _ResolvedRoute | None:
    definitions = [
        (cls, getattr(cls, method_name))
        for cls in reversed(type(ctrl).mro())
        if cls is not Controller and cls is not object and method_name in cls.__dict__
    ]
    if not any(hasattr(submethod, "original_routing") for _, submethod in definitions):
        return None

    merged_routing: dict[str, Any] = {"auth": "user", "methods": None, "routes": []}
    decorated: list[tuple[type, Any]] = []
    for cls, submethod in definitions:
        try:
            if not hasattr(submethod, "original_routing"):
                _debug.logic(
                    "http.route.override_unrouted",
                    controller=cls.__qualname__,
                    method=method_name,
                )
                e = (
                    f"{cls.__module__}.{cls.__name__}.{method_name} overrides a "
                    f"route without @route(). An undecorated override cannot be "
                    f"served: the URL would answer with whichever body the "
                    f"framework picked, not the one you wrote. Decorate it "
                    f"(@route() with no arguments inherits the parent's routing)."
                )
                raise RouteDefinitionError(e)
            fragment = _prepare_route_fragment(cls, submethod, merged_routing)
        except RouteDefinitionError as exc:
            _logger.error("%s The route is not served.", exc)
            _debug.logic(
                "http.route.skipped", reason="definition_error", method=method_name
            )
            return None
        decorated.append((cls, submethod))
        merged_routing.update(fragment)

    owner, implementation = decorated[-1]
    if not merged_routing["routes"]:
        _logger.warning(
            "%s is a controller endpoint without any route, skipping.",
            f"{owner.__module__}.{owner.__name__}.{method_name}",
        )
        _debug.logic("http.route.skipped", reason="no_routes", method=method_name)
        return None

    _check_cors_credentials(f"{type(ctrl).__name__}.{method_name}", merged_routing)
    merged_routing.setdefault("save_session", merged_routing["auth"] != "bearer")

    specs: dict[str, ParamSpec] | None = None
    if merged_routing.get("typed"):
        specs = {}
        for _cls, submethod in decorated:
            specs = get_param_specs(submethod.original_endpoint, specs)
    return _ResolvedRoute(
        merged_routing, implementation.__get__(ctrl, type(ctrl)), specs
    )


def _generate_routing_rules(
    modules: list[str], nodb_only: bool
) -> Generator[tuple[str, Endpoint]]:
    controllers = endpoints = rules = skipped_nodb = typed = 0  # debuglog
    for ctrl in _get_controllers(modules):
        controllers += 1  # debuglog
        for method_name, _member in inspect.getmembers(ctrl, inspect.ismethod):
            resolved = _resolve_route(ctrl, method_name)
            if resolved is None:
                continue
            merged_routing, method, param_specs = resolved
            if nodb_only and merged_routing["auth"] != "none":
                skipped_nodb += 1  # debuglog
                continue

            frozen_routing = MappingProxyType(merged_routing)
            endpoints += 1  # debuglog
            typed += bool(param_specs)  # debuglog

            for url in merged_routing["routes"]:
                partial = functools.partial(method)
                functools.update_wrapper(partial, method)
                endpoint = cast("Endpoint", partial)
                endpoint.routing = frozen_routing
                _apply_param_specs(endpoint, param_specs)
                rules += 1  # debuglog

                yield (url, endpoint)
    _debug.pipeline(
        "http.routing.rules_generated",
        nodb_only=nodb_only,
        controllers=controllers,
        endpoints=endpoints,
        rules=rules,
        typed=typed,
        skipped_nodb=skipped_nodb,
    )


def _prepare_route_fragment(
    controller_cls: type, submethod: Any, merged_routing: dict[str, Any]
) -> dict[str, Any]:
    fragment = dict(submethod.original_routing)

    routing_type = merged_routing.setdefault("type", fragment.get("type", "http"))
    declared_type = fragment.get("type")
    if declared_type not in (None, routing_type):
        where = f"{controller_cls.__module__}.{controller_cls.__name__}.{submethod.__name__}"
        _debug.logic(
            "http.route.type_conflict",
            where=where,
            parent=routing_type,
            override=declared_type,
        )
        e = (
            f"{where} overrides a type={routing_type!r} route with "
            f"type={declared_type!r}. One URL has one dispatcher, so the merged "
            f"route would keep {routing_type!r} -- but the override's own "
            f"@route(type=...) still decides how its return value is wrapped, so "
            f"the two disagree and every request to the route fails. Drop the "
            f"type= from the override, or give the override its own route."
        )
        raise RouteDefinitionError(e)
    fragment["type"] = routing_type

    if bool(fragment.get("typed", merged_routing.get("typed", False))):
        fragment["typed"] = True

    default_auth = fragment.get("auth", merged_routing["auth"])
    default_mode = fragment.get("readonly", default_auth == "none")
    parent_readonly = merged_routing.setdefault("readonly", default_mode)
    child_readonly = fragment.get("readonly")
    if child_readonly not in (None, parent_readonly) and not callable(child_readonly):
        _logger.warning(
            "The endpoint %s made the route %s although its parent was defined as %s. Setting the route read/write.",
            f"{controller_cls.__module__}.{controller_cls.__name__}.{submethod.__name__}",
            "readonly" if child_readonly else "read/write",
            "readonly" if parent_readonly else "read/write",
        )
        _debug.logic(
            "http.route.readonly_conflict",
            method=submethod.__name__,
            parent_readonly=bool(parent_readonly),
            child_readonly=bool(child_readonly),
        )
        fragment["readonly"] = False
    return fragment


def fragment_to_query_string(func: Callable) -> Callable:
    @functools.wraps(func)
    def fragment_wrapper(self, *a, **kw):
        if not (kw.keys() - {"debug"}):
            _debug.logic("http.route.fragment_redirect", endpoint=func.__qualname__)
            return Response("""<!DOCTYPE html>
            <html><head><script>
                (function () {
                    const url = window.location;
                    const fragment = url.hash.substring(1);
                    let new_url = url.pathname + url.search;
                    if (fragment.length !== 0) {
                        const separator = url.search ? (url.search === '?' ? '' : '&') : '?';
                        new_url = url.pathname + url.search + separator + fragment;
                    }
                    if (new_url == url.pathname) {
                        new_url = '/';
                    }
                    window.location = new_url;
                })()
            </script></head><body></body></html>""")
        return func(self, *a, **kw)

    return fragment_wrapper
