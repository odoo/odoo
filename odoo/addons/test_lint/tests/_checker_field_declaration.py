import ast
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass

# Hook attributes that name a method, with the family prefix §2.4.1 reserves.
HOOK_PREFIXES = {
    "compute": "_compute_",
    "inverse": "_inverse_",
    "search": "_search_",
    "selection": "_selection_",
}

# A call whose value is meant per record, so `default=` wants the callable,
# not what it returned once at import.
CALLED_ONCE_AT_IMPORT = frozenset(
    {
        "today",
        "now",
        "utcnow",
        "context_today",
        "context_now",
        "uuid4",
        "uuid1",
        "token_hex",
        "token_urlsafe",
        "token_bytes",
        "random",
        "randint",
        "choice",
        "time",
        "_",
    }
)

# The positional parameters of each field class's __init__, in order; every
# other class takes the label first. A positional argument is spelled as the
# keyword this table names.
POSITIONAL_PARAMETERS: dict[str, tuple[str, ...]] = {
    "Many2one": ("comodel_name", "string"),
    "One2many": ("comodel_name", "inverse_name", "string"),
    "Many2many": ("comodel_name", "relation", "column1", "column2", "string"),
    "Selection": ("selection", "string"),
    "Reference": ("selection", "string"),
    "Count": ("count_of", "string"),
    "Float": ("string", "digits", "min_display_digits"),
    "Monetary": ("string", "currency_field"),
}
_DEFAULT_POSITIONAL = ("string",)

# The order a declaration's keywords are read in: what the field is, what it
# says, its shape, how its value is produced, how it is stored and read, what
# it points at and under which conditions, who tracks it -- then, last of
# all, who may see it and the help text. An attribute the table does not know
# sorts alphabetically before that tail.
FIELD_ATTRIBUTE_ORDER: tuple[str, ...] = (
    "comodel_name",
    "inverse_name",
    "relation",
    "column1",
    "column2",
    "selection",
    "selection_add",
    "related",
    "count_of",
    "model_field",
    "definition",
    "definition_record",
    "definition_record_field",
    "delegate",
    "string",
    "export_string_translation",
    "size",
    "trim",
    "digits",
    "min_display_digits",
    "currency_field",
    "translate",
    "sanitize",
    "sanitize_overridable",
    "sanitize_tags",
    "sanitize_attributes",
    "sanitize_style",
    "sanitize_form",
    "sanitize_conditional_comments",
    "sanitize_output_method",
    "strip_style",
    "strip_classes",
    "attachment",
    "max_width",
    "max_height",
    "verify_resolution",
    "bin_size_field",
    "validate",
    "compute",
    "inverse",
    "search",
    "depends",
    "depends_context",
    "precompute",
    "compute_sudo",
    "related_sudo",
    "recursive",
    "inherited",
    "default",
    "change_default",
    "store",
    "index",
    "copy",
    "readonly",
    "required",
    "prefetch",
    "exportable",
    "company_dependent",
    "config_parameter",
    "aggregator",
    "group_expand",
    "falsy_value",
    "falsy_value_label",
    "domain",
    "context",
    "ondelete",
    "check_company",
    "bypass_search_access",
    "auto_join",
    "tracking",
    "implied_group",
    "write_groups",
    "groups",
    "help",
)
_TAIL: tuple[str, ...] = ("write_groups", "groups", "help")
_RANK = {name: index for index, name in enumerate(FIELD_ATTRIBUTE_ORDER)}


def positional_names(call: ast.Call) -> tuple[str, ...]:
    return POSITIONAL_PARAMETERS.get(call.func.attr, _DEFAULT_POSITIONAL)


def canonical_order(names: list[str]) -> list[str]:
    known = sorted(
        (n for n in names if n in _RANK and n not in _TAIL), key=_RANK.__getitem__
    )
    unknown = sorted(n for n in names if n not in _RANK)
    tail = sorted((n for n in names if n in _TAIL), key=_RANK.__getitem__)
    return known + unknown + tail


@dataclass
class Violation:
    lineno: int
    col_offset: int
    rule: str
    message: str


def is_field_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "fields"
        and node.func.attr[:1].isupper()
    )


def keywords(call: ast.Call) -> dict[str, ast.expr]:
    return {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}


def string_argument(call: ast.Call) -> ast.expr | None:
    if (value := keywords(call).get("string")) is not None:
        return value
    names = positional_names(call)
    position = names.index("string") if "string" in names else len(names)
    if len(call.args) > position and not isinstance(call.args[position], ast.Starred):
        return call.args[position]
    return None


def selection_argument(call: ast.Call) -> ast.expr | None:
    if (value := keywords(call).get("selection")) is not None:
        return value
    if call.func.attr == "Selection" and call.args:
        return call.args[0]
    return None


def _callee_tail(node: ast.expr) -> str:
    match node:
        case ast.Attribute(attr=attr):
            return attr
        case ast.Name(id=name):
            return name
    return ""


def _constant_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _check_default(name: str, call: ast.Call) -> Iterator[Violation]:
    default = keywords(call).get("default")
    if not isinstance(default, ast.Call):
        return
    tail = _callee_tail(default.func)
    if tail in CALLED_ONCE_AT_IMPORT:
        yield Violation(
            default.lineno,
            default.col_offset,
            "default-evaluated-at-import",
            f"{name}: default={ast.unparse(default)} ran once, when the module "
            f"was imported; pass the callable, default={ast.unparse(default.func)}",
        )


def _check_selection(name: str, call: ast.Call) -> Iterator[Violation]:
    selection = selection_argument(call)
    if not isinstance(selection, (ast.List, ast.Tuple)):
        return
    keys = [
        _constant_str(entry.elts[0])
        for entry in selection.elts
        if isinstance(entry, (ast.Tuple, ast.List)) and len(entry.elts) == 2
    ]
    for key, count in Counter(keys).items():
        if key is not None and count > 1:
            yield Violation(
                selection.lineno,
                selection.col_offset,
                "selection-duplicate-key",
                f"{name}: selection key {key!r} appears {count} times; dict() "
                "keeps the last label and the others are dead",
            )


def _check_hooks(name: str, call: ast.Call) -> Iterator[Violation]:
    for attribute, prefix in HOOK_PREFIXES.items():
        method = _constant_str(keywords(call).get(attribute))
        if method is not None and not method.startswith(prefix):
            yield Violation(
                call.lineno,
                call.col_offset,
                "field-hook-prefix",
                f"{name}: {attribute}={method!r} names a method outside the "
                f"{prefix}* family that {attribute}= is reserved for",
            )


def bound_names(statement: ast.stmt) -> list[str]:
    match statement:
        case ast.Assign(targets=targets):
            return [t.id for t in targets if isinstance(t, ast.Name)]
        case ast.AnnAssign(target=ast.Name(id=name), value=value) if value is not None:
            return [name]
    return []


def _check_positional(name: str, call: ast.Call) -> Iterator[Violation]:
    if not call.args:
        return
    names = positional_names(call)
    spelled = ", ".join(
        f"{names[i]}=" if i < len(names) else "?"
        for i, arg in enumerate(call.args)
        if not isinstance(arg, ast.Starred)
    )
    yield Violation(
        call.lineno,
        call.col_offset,
        "field-positional-argument",
        f"{name}: {len(call.args)} positional argument(s); spell them as {spelled}",
    )


def _check_layout(name: str, call: ast.Call) -> Iterator[Violation]:
    names = [k.arg for k in call.keywords if k.arg]
    if names != canonical_order(names):
        yield Violation(
            call.lineno,
            call.col_offset,
            "field-attribute-order",
            f"{name}: keywords read {', '.join(names)}; the order is "
            f"{', '.join(canonical_order(names))}",
        )
        return
    if len(call.keywords) < 2:
        return
    lines = [k.lineno for k in call.keywords]
    if len(set(lines)) != len(lines) or lines[0] == call.lineno:
        yield Violation(
            call.lineno,
            call.col_offset,
            "field-attribute-order",
            f"{name}: {len(call.keywords)} keywords share a line; one per line, "
            "none on the line of the call",
        )


def _check_dead(name: str, call: ast.Call) -> Iterator[Violation]:
    keys = keywords(call)
    kind = call.func.attr

    def truthy(key: str) -> bool:
        value = keys.get(key)
        return value is not None and not (
            isinstance(value, ast.Constant) and not value.value
        )

    # A declaration that states no compute= may be extending a stored one
    # from another module, so store= is judged only beside the compute it
    # belongs to.
    stored = truthy("store")
    computed_here = "compute" in keys
    if truthy("index") and (
        kind in ("One2many", "Many2many") or (computed_here and not stored)
    ):
        yield Violation(
            call.lineno,
            call.col_offset,
            "dead-field-attribute",
            f"{name}: index= on a field with no column",
        )
    if truthy("precompute") and computed_here and not stored:
        yield Violation(
            call.lineno,
            call.col_offset,
            "dead-field-attribute",
            f"{name}: precompute= without store=True is dropped at setup",
        )
    if truthy("related") and "compute" in keys:
        yield Violation(
            call.lineno,
            call.col_offset,
            "dead-field-attribute",
            f"{name}: compute= on a related field is replaced by the related "
            "path's own compute",
        )


def _check_stored_related(name: str, call: ast.Call) -> Iterator[Violation]:
    # Binary and Image are left out: `image_128 = Image(related="image_1920",
    # max_width=128, store=True)` stores a resize, not a copy of a column.
    if call.func.attr in ("Binary", "Image"):
        return
    keys = keywords(call)
    related, store = keys.get("related"), keys.get("store")
    if (
        isinstance(related, ast.Constant)
        and isinstance(related.value, str)
        and isinstance(store, ast.Constant)
        and store.value is True
    ):
        yield Violation(
            call.lineno,
            call.col_offset,
            "stored-related",
            f"{name}: a stored copy of {related.value}",
        )


def _check_class(node: ast.ClassDef) -> Iterator[Violation]:
    bound: dict[str, int] = {}
    for statement in node.body:
        targets = bound_names(statement)
        if not targets:
            continue
        is_field = is_field_call(statement.value)
        for target in targets:
            if target in bound and (is_field or bound[target] < 0):
                yield Violation(
                    statement.lineno,
                    statement.col_offset,
                    "field-redeclared",
                    f"{node.name}.{target} is declared again here, so the "
                    f"declaration at line {abs(bound[target])} is dead",
                )
            bound[target] = -statement.lineno if is_field else statement.lineno
        if not is_field or len(targets) != 1:
            continue
        name = targets[0]
        call = statement.value
        yield from _check_default(name, call)
        yield from _check_selection(name, call)
        yield from _check_hooks(name, call)
        yield from _check_positional(name, call)
        yield from _check_layout(name, call)
        yield from _check_dead(name, call)
        yield from _check_stored_related(name, call)


def check(tree: ast.Module, nodes=None) -> Iterator[Violation]:
    for node in nodes if nodes is not None else ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            yield from _check_class(node)
