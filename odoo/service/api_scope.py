from __future__ import annotations

import contextlib
import contextvars
import difflib
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NamedTuple

from lxml import etree

from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain

if TYPE_CHECKING:
    from odoo.api import Environment

OPERATIONS = ("read", "create", "write", "unlink", "call")

METHOD_OPERATIONS: Mapping[str, str] = {
    "search": "read",
    "search_read": "read",
    "search_count": "read",
    "read": "read",
    "name_search": "read",
    "web_name_search": "read",
    "fields_get": "read",
    "get_views": "read",
    "export_data": "read",
    "default_get": "read",
    "get_metadata": "read",
    "get_formview_id": "read",
    "get_formview_action": "read",
    "check_access": "read",
    "read_group": "read",
    "formatted_read_group": "read",
    "formatted_read_grouping_sets": "read",
    "web_read": "read",
    "web_search_read": "read",
    "web_read_group": "read",
    "create": "create",
    "copy": "create",
    "name_create": "create",
    "write": "write",
    "toggle_active": "write",
    "action_archive": "write",
    "action_unarchive": "write",
    "message_post": "write",
    "unlink": "unlink",
}

READ_RESULT_METHODS = frozenset({"read", "search_read", "web_read"})

# The context keys an API caller may set. An allowlist, because `call_kw`
# replaces the environment's context with the caller's and `default_<field>`
# or the `show_*` label embeds would reach around a denial.
SAFE_CONTEXT_KEYS = frozenset(
    {"lang", "tz", "allowed_company_ids", "active_test", "bin_size"}
)

# The record's label is what a many2one tuple carries whether or not it is
# asked for, and `res.partner` declares it dependent on `vat` for an optional
# rendering. Hiding it would strip the one field every answer needs while the
# tuple still shows it.
NEVER_HIDDEN = frozenset({"display_name"})

_SEGMENT_SEPARATORS = re.compile(r"[./]")
_SUBDOMAIN_OPERATORS = frozenset({"any", "not any"})
# Command.CREATE and Command.UPDATE carry a vals dict for the comodel.
_VALS_COMMANDS = frozenset({0, 1})


@dataclass(frozen=True)
class ModelRule:
    read: bool = True
    create: bool = False
    write: bool = False
    unlink: bool = False
    call: bool = False
    denied: frozenset[str] = frozenset()

    def allows(self, operation: str) -> bool:
        return bool(getattr(self, operation, False))


@dataclass(frozen=True)
class ScopeRules:
    """A scope as the guard reads it. `models` is None for a scope that names
    no model: every model the user may reach, every operation, nothing
    hidden -- the shape of a key generated with no scope in mind."""

    key: str
    models: Mapping[str, ModelRule] | None = None
    max_depth: int = 8
    # Per registry, keyed by model: the denylist closed over depends.
    _hidden: dict[str, frozenset[str]] = field(
        default_factory=dict, repr=False, compare=False
    )

    def rule(self, model_name: str) -> ModelRule | None:
        if self.models is None:
            return ModelRule(True, True, True, True, True)
        return self.models.get(model_name)

    def denied(self, model_name: str) -> frozenset[str]:
        rule = self.rule(model_name)
        return rule.denied if rule is not None else frozenset()


# The scope of the API call being served, for the ORM hooks that must know
# (the name search on `base`): a context variable, because `call_kw`
# replaces the environment's context with the caller's.
_ACTIVE: contextvars.ContextVar[ScopeRules | None] = contextvars.ContextVar(
    "api_scope", default=None
)


def active_rules() -> ScopeRules | None:
    return _ACTIVE.get()


@contextlib.contextmanager
def enforcing(rules: ScopeRules) -> Iterator[None]:
    token = _ACTIVE.set(rules)
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def operation_of(method: str) -> str:
    return METHOD_OPERATIONS.get(method, "call")


def check_model_operation(
    env: Environment, rules: ScopeRules, model_name: str, method: str
) -> None:
    rule = rules.rule(model_name)
    operation = operation_of(method)
    if rule is None:
        raise AccessError(  # noqa: E8505  the API key's own scope, named to its holder
            env._(
                "The API key's scope '%(scope)s' does not reach '%(model)s'.",
                scope=rules.key,
                model=model_name,
            )
        )
    if not rule.allows(operation):
        raise AccessError(  # noqa: E8505  the API key's own scope, named to its holder
            env._(
                "The API key's scope '%(scope)s' does not allow %(operation)s on "
                "'%(model)s' (%(method)s).",
                scope=rules.key,
                operation=operation,
                model=model_name,
                method=method,
            )
        )


def safe_context(env: Environment, context: Any) -> dict[str, Any]:
    """The caller's context reduced to keys that cannot reach around a denial:
    the environment's own safe keys, overridden only within the allowlist."""
    caller = context if isinstance(context, dict) else {}
    safe = {k: v for k, v in env.context.items() if k in SAFE_CONTEXT_KEYS}
    safe.update((k, v) for k, v in caller.items() if k in SAFE_CONTEXT_KEYS)
    return safe


# ---------------------------------------------------------------------------
# hidden fields: the denylist closed over depends
# ---------------------------------------------------------------------------


def hidden_field_names(
    env: Environment, rules: ScopeRules, model_name: str
) -> frozenset[str]:
    """The denylist closed over `@api.depends`.

    A `related` field is another name for a column, and a computed field is a
    function of its dependencies: `email_formatted` prints `email` verbatim,
    `same_vat_partner_id` answers whether a `vat` is taken. The registry has
    resolved every one of those through the depends map, so the walk reads it
    and reaches every field whose value derives from a hidden column, on this
    model or across a relation. Across a relation the other model's closure is
    consulted; two models hiding through each other fall back to the raw
    denylist rather than recursing.
    """
    cache = rules._hidden
    if model_name not in cache:
        cache[model_name] = _closed_field_names(
            env, rules, model_name, frozenset({model_name})
        )
    return cache[model_name]


def _closed_field_names(
    env: Environment, rules: ScopeRules, model_name: str, closing: frozenset[str]
) -> frozenset[str]:
    own = rules.denied(model_name)
    if not own and rules.models is None:
        return frozenset()
    if model_name not in env:
        return own
    model_fields = env[model_name]._fields
    depends = env.registry.field_depends
    hidden = set(own)
    grew = True
    while grew:
        grew = False
        for name, model_field in model_fields.items():
            if name in hidden or name in NEVER_HIDDEN:
                continue
            if any(
                _touches_hidden(env, rules, model_name, hidden, path, closing)
                for path in depends.get(model_field, ())
            ):
                hidden.add(name)
                grew = True
    return frozenset(hidden)


def _touches_hidden(
    env: Environment,
    rules: ScopeRules,
    model_name: str,
    hidden: set[str],
    path: str,
    closing: frozenset[str],
) -> bool:
    model = model_name
    for token in str(path).split("."):
        if model is None or model not in env:
            return False
        if model == model_name:
            names: frozenset[str] | set[str] = hidden
        elif model in closing:
            names = rules.denied(model)
        else:
            names = _closed_field_names(env, rules, model, closing | {model})
        if token in names:
            return True
        model_field = env[model]._fields.get(token)
        if model_field is None:
            return False
        model = getattr(model_field, "comodel_name", None)
    return False


def visible_name_search_fields(
    env: Environment, model_name: str, search_fnames: list[str]
) -> list[str]:
    """The name-search fields that touch no hidden column, or a refusal.

    `_rec_names_search` is how `display_name ilike`, `name_search` and a
    string operator on any many2one reach the columns behind a label --
    `res.partner` searches `vat` and `email` by name -- so a hidden column
    is a value oracle through every one of them. Dropping the hidden names
    narrows the search; when nothing is left, refusing beats matching
    everything, which is also what the ORM does for a cyclic list.
    """
    rules = active_rules()
    if rules is None:
        return list(search_fnames)
    visible = [
        fname
        for fname in search_fnames
        if not denied_along(env, rules, model_name, fname)
    ]
    if search_fnames and not visible:
        raise UserError(
            env._(
                "%(model)s cannot be searched by name through the API key's "
                "scope '%(scope)s': every field its name search reads is hidden.",
                model=model_name,
                scope=rules.key,
            )
        )
    return visible


# ---------------------------------------------------------------------------
# field paths
# ---------------------------------------------------------------------------


def _segment(token: str) -> str:
    return token.split(":", 1)[0].strip()


def path_segments(path: Any) -> list[str]:
    return _SEGMENT_SEPARATORS.split(str(path))


def walk_path(env: Environment, model_name: str, path: Any) -> list[tuple[str, str]]:
    """Every ``(model, field)`` a dotted or slashed path touches, in order."""
    pairs = []
    model: str | None = model_name
    for token in path_segments(path):
        name = _segment(token)
        if not name or model is None or model not in env:
            break
        pairs.append((model, name))
        model_field = env[model]._fields.get(name)
        model = (
            getattr(model_field, "comodel_name", None)
            if model_field is not None
            else None
        )
    return pairs


def denied_along(
    env: Environment, rules: ScopeRules, model_name: str, path: Any
) -> list[tuple[str, str]]:
    return [
        (model, name)
        for model, name in walk_path(env, model_name, path)
        if name in hidden_field_names(env, rules, model)
    ]


def default_projection(rules: ScopeRules, records: Any) -> list[str]:
    hidden = hidden_field_names(records.env, rules, records._name)
    model_fields = records._fields
    return [
        name
        for name in records._get_fields_default_read()
        if name not in hidden
        and model_fields[name].store
        and model_fields[name].type not in ("binary", "one2many", "many2many")
    ]


class Argument(NamedTuple):
    kind: str
    index: int | None
    name: str
    key: str | None = None


FIELDS, FIELD, PATHS, SPEC, DOMAIN, ORDER, GROUP, HAVING, VALS = (
    "fields",
    "field",
    "paths",
    "spec",
    "domain",
    "order",
    "group",
    "having",
    "vals",
)

# Where each RPC method takes the arguments that name fields.
CALL_SHAPES: dict[str, tuple[Argument, ...]] = {
    "read": (Argument(FIELDS, 1, "fields"),),
    "search": (Argument(DOMAIN, 0, "domain"), Argument(ORDER, 3, "order")),
    "search_count": (Argument(DOMAIN, 0, "domain"),),
    "search_read": (
        Argument(DOMAIN, 0, "domain"),
        Argument(FIELDS, 1, "fields"),
        Argument(ORDER, 4, "order"),
    ),
    "name_search": (Argument(DOMAIN, 1, "domain"),),
    "default_get": (Argument(FIELDS, 0, "fields"),),
    "load": (Argument(PATHS, 0, "fields"),),
    "export_data": (Argument(PATHS, 1, "fields_to_export"),),
    "get_field_translations": (Argument(FIELD, 1, "field_name"),),
    "update_field_translations": (Argument(FIELD, 1, "field_name"),),
    "search_panel_select_range": (Argument(FIELD, 0, "field_name"),),
    "search_panel_select_multi_range": (Argument(FIELD, 0, "field_name"),),
    "web_resequence": (
        Argument(SPEC, 1, "specification"),
        Argument(FIELD, 2, "field_name"),
    ),
    "create": (Argument(VALS, 0, "vals_list"),),
    "write": (Argument(VALS, 1, "vals"),),
    "copy": (Argument(VALS, 1, "default"),),
    "copy_data": (Argument(VALS, 1, "default"),),
    "onchange": (
        Argument(VALS, 1, "values"),
        Argument(FIELDS, 2, "field_names"),
        Argument(SPEC, 3, "fields_spec"),
    ),
    "read_group": (
        Argument(DOMAIN, 0, "domain"),
        Argument(GROUP, 1, "fields"),
        Argument(GROUP, 2, "groupby"),
        Argument(ORDER, 5, "orderby"),
    ),
    "formatted_read_group": (
        Argument(DOMAIN, 0, "domain"),
        Argument(GROUP, 1, "groupby"),
        Argument(GROUP, 2, "aggregates"),
        Argument(HAVING, 3, "having"),
        Argument(ORDER, 6, "order"),
    ),
    "formatted_read_grouping_sets": (
        Argument(DOMAIN, 0, "domain"),
        Argument(GROUP, 1, "grouping_sets"),
        Argument(GROUP, 2, "aggregates"),
        Argument(ORDER, None, "order"),
    ),
    "read_progress_bar": (
        Argument(DOMAIN, 0, "domain"),
        Argument(GROUP, 1, "group_by"),
        Argument(FIELD, 2, "progress_bar", "field"),
    ),
    "web_read": (Argument(SPEC, 1, "specification"),),
    "web_search_read": (
        Argument(DOMAIN, 0, "domain"),
        Argument(SPEC, 1, "specification"),
        Argument(ORDER, 4, "order"),
    ),
    "web_name_search": (
        Argument(SPEC, 1, "specification"),
        Argument(DOMAIN, 2, "domain"),
    ),
    "web_read_group": (
        Argument(DOMAIN, 0, "domain"),
        Argument(GROUP, 1, "groupby"),
        Argument(GROUP, 2, "aggregates"),
        Argument(ORDER, 5, "order"),
        Argument(SPEC, None, "unfold_read_specification"),
        Argument(SPEC, None, "groupby_read_specification"),
    ),
    "hierarchy_read": (
        Argument(DOMAIN, 0, "domain"),
        Argument(SPEC, 1, "specification"),
        Argument(FIELD, 2, "parent_field"),
        Argument(FIELD, 3, "child_field"),
        Argument(ORDER, 4, "order"),
    ),
    "web_save": (
        Argument(VALS, 1, "vals"),
        Argument(SPEC, 2, "specification"),
    ),
    "web_save_multi": (
        Argument(VALS, 1, "vals_list"),
        Argument(SPEC, 2, "specification"),
    ),
}


def arguments(method: str, kind: str, args: Any, kwargs: Mapping[str, Any]) -> list:
    found = []
    for argument in CALL_SHAPES.get(method, ()):
        if argument.kind != kind:
            continue
        value = kwargs.get(argument.name)
        if value is None and argument.index is not None and len(args) > argument.index:
            value = args[argument.index]
        if argument.key is not None:
            value = value.get(argument.key) if isinstance(value, dict) else None
        if value is not None:
            found.append(value)
    return found


def _leading_name(spec: Any) -> str:
    if not isinstance(spec, str):
        return ""
    head = spec
    for separator in (":", ".", "/"):
        head = head.split(separator, 1)[0]
    return head.strip()


def parse_domain(domain: Any) -> Domain | None:
    if isinstance(domain, Domain):
        return domain
    if not isinstance(domain, list | tuple):
        return None
    try:
        return Domain(list(domain))
    except ValueError, TypeError:
        return None


def domain_paths(domain: Any, prefix: str = "") -> list[str]:
    """Every field path a domain filters on, sub-domains of ``any`` included."""
    parsed = parse_domain(domain)
    if parsed is None:
        return []
    paths = []
    for condition in parsed.iter_conditions():
        path = f"{prefix}{condition.field_expr}"
        paths.append(path)
        if condition.operator in _SUBDOMAIN_OPERATORS:
            paths.extend(domain_paths(condition.value, prefix=f"{path}."))
    return paths


def order_paths(order: Any) -> list[str]:
    if not order or not isinstance(order, str):
        return []
    return [term.split()[0] for term in order.split(",") if term.strip()]


def _spec_paths(spec: Any, prefix: str = "") -> list[str]:
    if not isinstance(spec, dict):
        return []
    paths = []
    for name, sub in spec.items():
        if not isinstance(name, str) or not name or name.startswith("__"):
            continue
        path = f"{prefix}{name}"
        paths.append(path)
        if isinstance(sub, dict):
            paths.extend(_spec_paths(sub.get("fields") or {}, prefix=f"{path}."))
    return paths


def _container_paths(container: Any) -> list[str]:
    if isinstance(container, str):
        return [container]
    if isinstance(container, dict | list | tuple):
        return [name for name in container if isinstance(name, str)]
    return []


def _grouping_paths(container: Any) -> list[str]:
    if isinstance(container, str):
        return [container]
    if isinstance(container, list | tuple):
        return [p for item in container for p in _grouping_paths(item)]
    return []


def vals_paths(vals: Any, prefix: str = "") -> list[str]:
    """Every field path a vals dict writes, x2many command payloads included:
    ``{"child_ids": [[0, 0, {"vat": ...}]]}`` writes ``child_ids.vat``."""
    if not isinstance(vals, dict):
        return []
    paths = []
    for key, value in vals.items():
        if not isinstance(key, str):
            continue
        path = f"{prefix}{key}"
        paths.append(path)
        if isinstance(value, list | tuple):
            for command in value:
                if (
                    isinstance(command, list | tuple)
                    and len(command) == 3
                    and command[0] in _VALS_COMMANDS
                ):
                    paths.extend(vals_paths(command[2], prefix=f"{path}."))
    return paths


def _iter_vals_dicts(
    method: str, args: Any, kwargs: Mapping[str, Any]
) -> Iterator[dict]:
    for vals in arguments(method, VALS, args, kwargs):
        if isinstance(vals, dict):
            yield vals
        elif isinstance(vals, list | tuple):
            for item in vals:
                if isinstance(item, dict):
                    yield item


def call_paths(method: str, args: Any, kwargs: Mapping[str, Any]) -> list[str]:
    paths: list[str] = []
    for kind in (FIELDS, PATHS, FIELD):
        for container in arguments(method, kind, args, kwargs):
            paths.extend(_container_paths(container))
    for spec in arguments(method, SPEC, args, kwargs):
        paths.extend(_spec_paths(spec))
    for kind in (DOMAIN, HAVING):
        for domain in arguments(method, kind, args, kwargs):
            paths.extend(domain_paths(domain))
    for order in arguments(method, ORDER, args, kwargs):
        paths.extend(order_paths(order))
    for container in arguments(method, GROUP, args, kwargs):
        paths.extend(_grouping_paths(container))
    for vals in _iter_vals_dicts(method, args, kwargs):
        paths.extend(vals_paths(vals))
    return [p for p in paths if p and not _segment(p).startswith("__")]


# ---------------------------------------------------------------------------
# refusals
# ---------------------------------------------------------------------------


def _close_field_names(name: str, known: list[str]) -> list[str]:
    tokens = frozenset(name.split("_"))
    reordered = [k for k in known if frozenset(k.split("_")) == tokens and k != name]
    if reordered:
        return reordered[:2]
    return difflib.get_close_matches(name, known, n=2, cutoff=0.5)


def _describe_unknown(name: Any, known: list[str]) -> str:
    if not isinstance(name, str):
        return f"{name!r} (not a string)"
    close = _close_field_names(name, known)
    if close:
        return f"{name!r} (did you mean {' or '.join(repr(c) for c in close)}?)"
    return repr(name)


def unknown_field_names(env: Environment, model_name: str, names: Any) -> str:
    """The names the model has no field for, each with what the caller
    probably meant, or an empty string."""
    model_fields = env[model_name]._fields
    unknown: list = []
    for name in names:
        if isinstance(name, str) and (not name or name.startswith("__")):
            continue
        if (isinstance(name, str) and name in model_fields) or name in unknown:
            continue
        unknown.append(name)
    if not unknown:
        return ""
    known = sorted(model_fields)
    return ", ".join(_describe_unknown(name, known) for name in unknown)


def _refuse_unknown(
    env: Environment, model_name: str, unknown: str, where: str
) -> None:
    raise UserError(
        env._(
            "Unknown field(s) %(where)s'%(model)s': %(fields)s. Call "
            "fields_get('%(model)s') for the fields this model actually has.",
            where=where,
            model=model_name,
            fields=unknown,
        )
    )


def check_requested_fields(
    env: Environment, model_name: str, method: str, args: Any, kwargs: Mapping[str, Any]
) -> None:
    names: list = []
    for kind in (FIELDS, PATHS, FIELD, SPEC):
        for container in arguments(method, kind, args, kwargs):
            if kind is FIELD:
                names.extend(
                    [_leading_name(container)] if isinstance(container, str) else []
                )
            elif isinstance(container, dict | list | tuple):
                names.extend(
                    _leading_name(name) if kind is PATHS else name for name in container
                )
    if names and (unknown := unknown_field_names(env, model_name, names)):
        _refuse_unknown(env, model_name, unknown, env._("on "))


def check_domain(
    env: Environment, model_name: str, method: str, args: Any, kwargs: Mapping[str, Any]
) -> None:
    domains = arguments(method, DOMAIN, args, kwargs)
    domain = domains[0] if domains else None
    if domain is None or isinstance(domain, Domain):
        return
    if not isinstance(domain, list | tuple):
        raise UserError(
            env._(
                "The domain for '%(model)s' must be a list, got %(kind)s.",
                model=model_name,
                kind=type(domain).__name__,
            )
        )
    model = env[model_name]
    try:
        parsed = Domain(list(domain))
    except (ValueError, TypeError) as e:
        raise UserError(
            env._(
                "Malformed domain for '%(model)s': %(error)s", model=model_name, error=e
            )
        ) from e
    names = [_leading_name(str(c.field_expr)) for c in parsed.iter_conditions()]
    if unknown := unknown_field_names(env, model_name, names):
        _refuse_unknown(env, model_name, unknown, env._("in the domain for "))
    try:
        parsed.check(model)
    except (ValueError, TypeError) as e:
        raise UserError(
            env._(
                "Invalid domain for '%(model)s': %(error)s", model=model_name, error=e
            )
        ) from e


def check_order(
    env: Environment, model_name: str, method: str, args: Any, kwargs: Mapping[str, Any]
) -> None:
    model_fields = env[model_name]._fields
    unknown: list[str] = []
    for order in arguments(method, ORDER, args, kwargs):
        if not order or not isinstance(order, str):
            continue
        for term in order.split(","):
            parts = term.split()
            if not parts:
                continue
            head, _, rest = parts[0].partition(".")
            head = head.split(":", 1)[0]
            if not head:
                continue
            model_field = model_fields.get(head)
            if model_field is None:
                if head not in unknown:
                    unknown.append(head)
                continue
            if rest and not getattr(model_field, "is_properties", False):
                raise UserError(
                    env._(
                        "Cannot sort '%(model)s' by '%(term)s': '%(head)s' is a "
                        "relation, and sorting across a relation is not "
                        "supported. Sort by a field of '%(model)s' itself.",
                        model=model_name,
                        term=parts[0],
                        head=head,
                    )
                )
    if unknown and (described := unknown_field_names(env, model_name, unknown)):
        _refuse_unknown(env, model_name, described, env._("in the sort order for "))


def check_grouping(
    env: Environment, model_name: str, method: str, args: Any, kwargs: Mapping[str, Any]
) -> None:
    names: list[str] = []
    for container in arguments(method, GROUP, args, kwargs):
        names.extend(_leading_name(spec) for spec in _grouping_paths(container))
    for having in arguments(method, HAVING, args, kwargs):
        parsed = parse_domain(having)
        if parsed is not None:
            names.extend(
                _leading_name(str(c.field_expr)) for c in parsed.iter_conditions()
            )
    if unknown := unknown_field_names(env, model_name, [n for n in names if n]):
        _refuse_unknown(
            env, model_name, unknown, env._("in the group specification for ")
        )


def check_write_values(
    env: Environment, model_name: str, method: str, args: Any, kwargs: Mapping[str, Any]
) -> None:
    keys = [key for vals in _iter_vals_dicts(method, args, kwargs) for key in vals]
    if unknown := unknown_field_names(env, model_name, keys):
        _refuse_unknown(env, model_name, unknown, env._("on "))


def check_field_names(
    env: Environment, model_name: str, method: str, args: Any, kwargs: Mapping[str, Any]
) -> None:
    """Every field name the call mentions exists, with what the caller
    probably meant when one does not."""
    check_requested_fields(env, model_name, method, args, kwargs)
    check_domain(env, model_name, method, args, kwargs)
    check_order(env, model_name, method, args, kwargs)
    check_grouping(env, model_name, method, args, kwargs)
    check_write_values(env, model_name, method, args, kwargs)


def _describe_hits(hits: list[tuple[str, str]]) -> str:
    return ", ".join(f"{name} (on {model})" for model, name in hits)


def check_hidden_paths(
    env: Environment,
    rules: ScopeRules,
    model_name: str,
    paths: list,
    where: str | None = None,
) -> None:
    hits: list[tuple[str, str]] = []
    too_deep: list[str] = []
    for path in paths:
        # Refusing beats truncating: a denied field past the cap would be
        # served instead of found.
        if len(path_segments(path)) > rules.max_depth:
            too_deep.append(str(path))
            continue
        hits.extend(denied_along(env, rules, model_name, path))
    if too_deep:
        raise UserError(
            env._(
                "%(paths)s cannot be checked against the API key's scope: a "
                "path may not cross more than %(cap)s segments%(where)s.",
                paths=", ".join(sorted(set(too_deep))),
                cap=rules.max_depth,
                where=env._(" in %(call)s", call=where) if where else "",
            )
        )
    if hits:
        hits = sorted(set(hits))
        raise UserError(
            env._(
                "%(fields)s %(verb)s not available through the API key's scope "
                "'%(scope)s'%(where)s.",
                fields=_describe_hits(hits),
                verb=env._("is") if len(hits) == 1 else env._("are"),
                scope=rules.key,
                where=env._(" in %(call)s", call=where) if where else "",
            )
        )


def check_call(
    env: Environment,
    rules: ScopeRules,
    model_name: str,
    method: str,
    args: Any,
    kwargs: Mapping[str, Any],
) -> None:
    check_model_operation(env, rules, model_name, method)
    check_field_names(env, model_name, method, args, kwargs)
    check_hidden_paths(env, rules, model_name, call_paths(method, args, kwargs))


# ---------------------------------------------------------------------------
# results
# ---------------------------------------------------------------------------


def strip(
    env: Environment, rules: ScopeRules, model_name: str, result: Any, _depth: int = 0
) -> Any:
    if _depth > rules.max_depth:
        # Past the cap a hidden column cannot be told from a visible one.
        return None
    if not model_name or model_name not in env:
        return result
    if isinstance(result, list):
        return [strip(env, rules, model_name, row, _depth) for row in result]
    if not isinstance(result, dict):
        return result
    hidden = hidden_field_names(env, rules, model_name)
    model_fields = env[model_name]._fields
    stripped = {}
    for key, value in result.items():
        name = _segment(key) if isinstance(key, str) else key
        if name in hidden:
            continue
        model_field = model_fields.get(name)
        comodel = (
            getattr(model_field, "comodel_name", None)
            if model_field is not None
            else None
        )
        if comodel and isinstance(value, dict | list):
            stripped[key] = strip(env, rules, comodel, value, _depth + 1)
        else:
            stripped[key] = value
    return stripped


def strip_fields_get(
    env: Environment, rules: ScopeRules, model_name: str, result: Any
) -> Any:
    if not isinstance(result, dict):
        return result
    hidden = hidden_field_names(env, rules, model_name)
    return {k: v for k, v in result.items() if k not in hidden}


def strip_arch(env: Environment, rules: ScopeRules, model_name: str, arch: str) -> str:
    try:
        root = etree.fromstring(arch)
    except etree.XMLSyntaxError:
        return arch
    _strip_arch_node(env, rules, model_name, root)
    return etree.tostring(root, encoding="unicode")


def _strip_arch_node(
    env: Environment, rules: ScopeRules, model_name: str, node: Any
) -> None:
    model_fields = env[model_name]._fields if model_name in env else {}
    hidden = (
        hidden_field_names(env, rules, model_name) if model_name in env else frozenset()
    )
    for child in list(node):
        if not isinstance(child.tag, str):
            continue
        if child.tag != "field":
            _strip_arch_node(env, rules, model_name, child)
            continue
        name = child.get("name")
        if name in hidden:
            node.remove(child)
            continue
        model_field = model_fields.get(name)
        comodel = (
            getattr(model_field, "comodel_name", None)
            if model_field is not None
            else None
        )
        _strip_arch_node(env, rules, comodel or model_name, child)


def strip_views(
    env: Environment, rules: ScopeRules, model_name: str, result: Any
) -> Any:
    """``get_views`` is ``fields_get`` for every model the views touch plus an
    arch that names each field: both halves take the same decision."""
    if not isinstance(result, dict):
        return result
    models = {
        name: {**spec, "fields": strip_fields_get(env, rules, name, spec.get("fields"))}
        if isinstance(spec, dict)
        else spec
        for name, spec in (result.get("models") or {}).items()
    }
    views = {
        kind: {**view, "arch": strip_arch(env, rules, model_name, view["arch"])}
        if isinstance(view, dict) and isinstance(view.get("arch"), str)
        else view
        for kind, view in (result.get("views") or {}).items()
    }
    return {**result, "models": models, "views": views}


def strip_export(
    env: Environment, rules: ScopeRules, model_name: str, paths: Any, result: Any
) -> Any:
    """``export_data`` answers positionally, so a hidden column is an index;
    the check before the call is the first line and this the second."""
    if not isinstance(result, dict) or "datas" not in result:
        return result
    keep = [
        index
        for index, path in enumerate(paths or [])
        if len(path_segments(path)) <= rules.max_depth
        and not denied_along(env, rules, model_name, path)
    ]
    if len(keep) == len(paths or []):
        return result
    return {
        **result,
        "datas": [
            [row[i] for i in keep if i < len(row)] if isinstance(row, list) else row
            for row in result.get("datas") or []
        ],
    }


def filter_result(
    env: Environment,
    rules: ScopeRules,
    model_name: str,
    method: str,
    args: Any,
    kwargs: Mapping[str, Any],
    result: Any,
) -> Any:
    if method == "fields_get":
        return strip_fields_get(env, rules, model_name, result)
    if method == "get_views":
        return strip_views(env, rules, model_name, result)
    if method == "export_data":
        requested = arguments(method, PATHS, args, kwargs)
        return strip_export(
            env, rules, model_name, requested[0] if requested else [], result
        )
    if method in READ_RESULT_METHODS:
        return strip(env, rules, model_name, result)
    return result
