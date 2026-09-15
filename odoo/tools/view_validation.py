import ast
import collections
import functools
import logging
import typing
from pathlib import Path

from lxml import etree

from odoo import tools
from odoo.libs.debug_log import DebugLog
from odoo.tools import view_ir

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    type Validator = Callable[..., bool]

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


_validators: collections.defaultdict[str, list[Validator]] = collections.defaultdict(
    list
)
_relaxng_cache: dict[str, etree.RelaxNG | None] = {}

# view type -> the module-relative path of the RelaxNG schema that validates its
# arch, or None for a type that deliberately has none. A view type declares its
# entry with register_schema(); `valid_view` consults this before running the
# per-tag predicates, so a type is schema-validated because it said it has a
# schema and not because it was added to a decorator in this file.
#
# None is a meaningful declaration, not an absence: `form` and `kanban` are
# qweb-based and validated structurally by the element handlers of ir_ui_view_arch, and
# saying so here is what lets a gate tell them apart from a type whose author
# forgot.
_view_schemas: dict[str, str | None] = {}

IGNORED_IN_EXPRESSION = {
    "True",
    "False",
    "None",
    "self",
    "uid",
    "context",
    "context_today",
    "allowed_company_ids",
    "current_company_id",
    "time",
    "datetime",
    "relativedelta",
    "current_date",
    "today",
    "now",
    "abs",
    "len",
    "bool",
    "float",
    "str",
    "set",
}


@functools.cache
def domain_operators() -> frozenset[str]:
    import odoo.orm.domain as domains

    return frozenset(
        {
            domains.DomainNot.OPERATOR,
            domains.DomainAnd.OPERATOR,
            domains.DomainOr.OPERATOR,
        }
    )


def _filter_contextual_names(contextual_values: set[str]) -> set[str]:
    value_names = set()
    for name in contextual_values:
        if name == "parent":
            continue
        root = name.split(".")[0]
        if root not in IGNORED_IN_EXPRESSION:
            value_names.add(name if root == "parent" else root)
    return value_names


_NESTED_DOMAIN_NODES = (ast.List, ast.IfExp, ast.BoolOp, ast.BinOp)


def _extract_domain_operand(
    node: ast.AST, contextual_values: set[str], field_names: set[str]
) -> None:
    if isinstance(node, _NESTED_DOMAIN_NODES):
        _extract_names_from_domain(node, contextual_values, field_names)
    else:
        contextual_values.update(_get_expression_contextual_values(node))


def _extract_domain_leaf(
    ast_item: ast.AST, contextual_values: set[str], field_names: set[str]
) -> None:
    if isinstance(ast_item, ast.Constant):
        if ast_item.value not in domain_operators() and ast_item.value not in (
            True,
            False,
        ):
            raise ValueError
        return
    if not isinstance(ast_item, (ast.List, ast.Tuple)):
        raise ValueError

    left, _operator, right = ast_item.elts
    contextual_values.update(_get_expression_contextual_values(right))
    if isinstance(left, ast.Constant) and isinstance(left.value, str):
        field_names.add(left.value)
    elif isinstance(left, ast.Constant) and left.value in (1, 0):
        pass
    elif isinstance(right, ast.Constant) and right.value == 1:
        contextual_values.update(_get_expression_contextual_values(left))
    else:
        raise ValueError


def _extract_names_from_domain(
    ast_domain: ast.AST, contextual_values: set[str], field_names: set[str]
) -> None:
    if isinstance(ast_domain, ast.IfExp):
        _extract_names_from_domain(ast_domain.body, contextual_values, field_names)
        _extract_names_from_domain(ast_domain.orelse, contextual_values, field_names)
        return
    if isinstance(ast_domain, ast.BoolOp):
        for value in ast_domain.values:
            _extract_domain_operand(value, contextual_values, field_names)
        return
    if isinstance(ast_domain, ast.BinOp):
        _extract_domain_operand(ast_domain.left, contextual_values, field_names)
        _extract_domain_operand(ast_domain.right, contextual_values, field_names)
        return
    if not isinstance(ast_domain, (ast.List, ast.Tuple)):
        raise ValueError
    for ast_item in ast_domain.elts:
        _extract_domain_leaf(ast_item, contextual_values, field_names)


def _extract_domain_list(domain: list, field_names: set[str]) -> None:
    for leaf in domain:
        if leaf in domain_operators() or leaf in (True, False):
            continue
        left, _operator, _right = leaf
        if isinstance(left, str):
            field_names.add(left)
        elif left not in (1, 0):
            raise ValueError


def get_domain_value_names(domain: list | str) -> tuple[set[str], set[str]]:
    contextual_values: set[str] = set()
    field_names: set[str] = set()

    try:
        if isinstance(domain, list):
            _extract_domain_list(domain, field_names)
        elif isinstance(domain, str):
            item_ast = ast.parse(f"({domain.strip()})", mode="eval").body
            if isinstance(item_ast, ast.Name):
                contextual_values.update(_get_expression_contextual_values(item_ast))
            else:
                _extract_names_from_domain(item_ast, contextual_values, field_names)

    except ValueError, TypeError, AttributeError:
        msg = "Wrong domain formatting."
        raise ValueError(msg) from None

    return field_names, _filter_contextual_names(contextual_values)


def _get_contextual_values_of_nodes(*nodes: ast.AST | None) -> set[str]:
    values: set[str] = set()
    for node in nodes:
        if node is not None:
            values |= _get_expression_contextual_values(node)
    return values


_CONTEXTUAL_CHILDREN: dict[type, Callable[[typing.Any], tuple]] = {
    ast.List: lambda n: tuple(n.elts),
    ast.Tuple: lambda n: tuple(n.elts),
    ast.Slice: lambda n: (n.lower, n.upper, n.step),
    ast.Subscript: lambda n: (n.value, n.slice),
    ast.Compare: lambda n: (n.left, *n.comparators),
    ast.BinOp: lambda n: (n.left, n.right),
    ast.BoolOp: lambda n: tuple(n.values),
    ast.UnaryOp: lambda n: (n.operand,),
    ast.Call: lambda n: (n.func, *n.args),
    ast.IfExp: lambda n: (n.test, n.body, n.orelse),
    ast.Dict: lambda n: (*n.keys, *n.values),
}


def _get_expression_contextual_values(item_ast: ast.AST) -> set[str]:
    if isinstance(item_ast, ast.Constant):
        return set()
    if isinstance(item_ast, ast.Name):
        return {item_ast.id}
    if isinstance(item_ast, ast.Attribute):
        values = _get_expression_contextual_values(item_ast.value)
        if len(values) == 1:
            return {f"{sorted(values).pop()}.{item_ast.attr}"}
        return values

    children = _CONTEXTUAL_CHILDREN.get(type(item_ast))
    if children is None:
        raise ValueError(f"Unsupported expression: {type(item_ast).__name__}.")
    return _get_contextual_values_of_nodes(*children(item_ast))


def get_expression_field_names(expression: str) -> set[str]:
    if not expression:
        return set()
    item_ast = ast.parse(expression.strip(), mode="eval").body
    contextual_values = _get_expression_contextual_values(item_ast)
    return _filter_contextual_names(contextual_values)


def get_dict_asts(expr: str | ast.AST) -> dict[str, ast.AST]:
    if isinstance(expr, str):
        expr = ast.parse(expr.strip(), mode="eval").body

    if not isinstance(expr, ast.Dict):
        msg = "Non-dict expression"
        raise ValueError(msg)
    if not all(
        (isinstance(key, ast.Constant) and isinstance(key.value, str))
        for key in expr.keys
    ):
        msg = "Non-string literal dict key"
        raise ValueError(msg)
    return {
        key.value: val  # type: ignore[union-attr]
        for key, val in zip(expr.keys, expr.values, strict=False)
    }


def valid_view(arch: etree._Element, **kwargs: object) -> bool:
    if not schema_valid(arch, **kwargs):
        _logger.warning("Invalid XML for view type %r: schema", arch.tag)
        return False
    if not ir_valid(arch):
        _logger.warning("Invalid XML for view type %r: view IR", arch.tag)
        return False
    for pred in _validators.get(arch.tag, ()):
        if not pred(arch, **kwargs):
            _logger.warning(
                "Invalid XML for view type %r: %s",
                arch.tag,
                pred.__doc__ or pred.__name__,
            )
            _debug.logic(
                "view_validation.predicate_rejected",
                view_type=arch.tag,
                predicate=pred.__name__,
            )
            return False
    _debug.pipeline(
        "view_validation.valid",
        view_type=arch.tag,
        predicates=len(_validators.get(arch.tag, ())),
        schema=_view_schemas.get(arch.tag) is not None,
    )
    return True


def ir_valid(arch: etree._Element) -> bool:
    """Reject what the view IR schema calls an error: a tag no view type knows,
    a required attribute missing, a value the attribute's type cannot read.
    Undeclared attributes are warnings there and do not fail here."""
    view_type = view_ir.schema().view_type_of(arch.tag)
    if view_type is None:
        _debug.logic("view_validation.ir_skipped", root=arch.tag)
        return True
    errors = [
        issue
        for issue in view_ir.get_issues(view_ir.from_arch(arch), view_type)
        if issue.severity == "error"
    ]
    for issue in errors:
        _logger.warning("%s", issue)
    _debug.logic(
        "view_validation.ir_checked",
        view_type=view_type,
        errors=len(errors),
        first=str(errors[0]) if errors else None,
    )
    return not errors


def register_validator(*view_types: str) -> Callable[[Validator], Validator]:
    def decorator(fn: Validator) -> Validator:
        for arch in view_types:
            _validators[arch].append(fn)
        _debug.lifecycle(
            "view_validation.validator_registered",
            predicate=fn.__name__,
            view_types=view_types,
        )
        return fn

    return decorator


def register_schema(view_type: str, path: str | None) -> None:
    """Declare which RelaxNG schema validates ``view_type``'s arch.

    ``path`` is module-relative, resolved through ``file_open`` like any other
    addon resource -- ``"web_gantt/rng/gantt_view.rng"``. Pass ``None`` to state
    that the type has no schema on purpose.

    Call it at import time, beside the ``ir.ui.view.type`` selection_add that
    introduces the type, so the type and its schema are declared together. A
    second registration for the same type replaces the first and drops the
    cached schema, which is what makes a module reloadable in tests.
    """
    _debug.lifecycle(
        "view_validation.schema_registered",
        view_type=view_type,
        path=path,
        replaced=view_type in _view_schemas,
    )
    if _view_schemas.get(view_type) != path:
        _relaxng_cache.pop(view_type, None)
    _view_schemas[view_type] = path


def registered_schemas() -> dict[str, str | None]:
    """The declared schema of every view type, for gates and tests to read."""
    return dict(_view_schemas)


def relaxng(view_type: str) -> etree.RelaxNG | None:
    """The compiled schema for ``view_type``, or None if it declared none."""
    if view_type not in _relaxng_cache:
        path = _view_schemas.get(view_type)
        if path is None:
            _relaxng_cache[view_type] = None
            return None
        try:
            with _debug.perf("view_validation.schema_compiled", view_type=view_type):
                with tools.file_open(path) as frng:
                    _relaxng_cache[view_type] = etree.RelaxNG(etree.parse(frng))
        except Exception as exc:
            _logger.exception(
                "Failed to load RelaxNG XML schema %r for view type %r",
                path,
                view_type,
            )
            _debug.logic(
                "view_validation.schema_load_failed",
                view_type=view_type,
                path=path,
                error=type(exc).__name__,
            )
            _relaxng_cache[view_type] = None
    return _relaxng_cache[view_type]


def schema_valid(arch: etree._Element, **kwargs: object) -> bool:
    """Check the arch against the schema its view type declared."""
    view_type = arch.tag
    if _view_schemas.get(view_type) is None:
        # Declared no schema, or is not a registered view type at all.
        _debug.logic(
            "view_validation.schema_absent",
            view_type=view_type,
            registered=view_type in _view_schemas,
        )
        return True
    validator = relaxng(view_type)
    if validator is None:
        # A declared schema that will not load is a packaging error, and
        # answering True here would turn it into silence: the type would stop
        # being validated and every arch would pass. Refuse instead, so the
        # first view of this type names the problem.
        _logger.error(
            "view type %r declares the RelaxNG schema %r, which failed to load",
            view_type,
            _view_schemas[view_type],
        )
        return False
    if not validator.validate(arch):
        for error in validator.error_log:
            _logger.warning("%s", error)
        _debug.logic(
            "view_validation.schema_rejected",
            view_type=view_type,
            errors=len(validator.error_log),
        )
        return False
    return True


for _view_type in ("activity", "calendar", "graph", "list", "pivot", "search"):
    register_schema(_view_type, str(Path("base", "rng", f"{_view_type}_view.rng")))
del _view_type


def att_names(name):
    yield name
    yield f"t-att-{name}"
    yield f"t-attf-{name}"


def get_dropdown_menu_warnings(node):
    warnings = []
    if any("dropdown-menu" in node.get(cl, "") for cl in att_names("class")):
        if node.get("role") != "menu":
            warnings.append("dropdown-menu class must have menu role")
    return warnings


def get_progress_bar_warnings(node):
    warnings = []
    if any("o_progressbar" in node.get(cl, "") for cl in att_names("class")):
        if node.get("role") != "progressbar":
            warnings.append("o_progressbar class must have progressbar role")
        if not any(node.get(at) for at in att_names("aria-valuenow")):
            warnings.append("o_progressbar class must have aria-valuenow attribute")
        if not any(node.get(at) for at in att_names("aria-valuemin")):
            warnings.append("o_progressbar class must have aria-valuemin attribute")
        if not any(node.get(at) for at in att_names("aria-valuemax")):
            warnings.append("o_progressbar class must have aria-valuemax attribute")
    return warnings


def get_fa_class_accessibility_warnings(node, description):
    valid_aria_attrs = {
        *att_names("title"),
        *att_names("aria-label"),
        *att_names("aria-labelledby"),
    }
    valid_t_attrs = {"t-value", "t-raw", "t-field", "t-esc", "t-out"}

    parent = node.getparent()
    if (node.tail or "").strip() or (
        parent is not None and (parent.text or "").strip()
    ):
        return []

    def has_text(elem):
        if elem is None:
            return False
        if elem.tag == "span" and elem.text:
            return True
        if elem.tag in ["field", "label"] and elem.get("string"):
            return True
        return bool(elem.tag == "t" and (elem.get("t-esc") or elem.get("t-raw")))

    if has_text(node.getnext()) or has_text(node.getprevious()):
        return []

    def has_title_or_aria_label(node):
        return any(node.get(attr) for attr in valid_aria_attrs)

    if any(map(has_title_or_aria_label, node.iterancestors())):
        return []

    if node.get("string"):
        return []

    def contains_description(node, depth=0):
        if any(node.get(attr) for attr in valid_t_attrs):
            return True
        if has_title_or_aria_label(node):
            return True
        if node.tag in ("label", "field"):
            return True
        if node.text:
            return True
        return any(contains_description(child, depth + 1) for child in node)

    if contains_description(node):
        return []

    return [
        "%s must have title in its tag, parents, descendants or have text" % description
    ]


def get_class_accessibility_warnings(node, expr):
    warnings = []
    classes = set(expr.split(" "))
    if "modal" in classes and node.get("role") != "dialog":
        warnings.append('"modal" class should only be used with "dialog" role')
    if "modal-header" in classes and node.tag != "header":
        warnings.append('"modal-header" class should only be used in "header" tag')
    if "modal-body" in classes and node.tag != "main":
        warnings.append('"modal-body" class should only be used in "main" tag')
    if "modal-footer" in classes and node.tag != "footer":
        warnings.append('"modal-footer" class should only be used in "footer" tag')
    if "tab-pane" in classes and node.get("role") != "tabpanel":
        warnings.append('"tab-pane" class should only be used with "tabpanel" role')
    if "nav-tabs" in classes and node.get("role") != "tablist":
        warnings.append('A tab list with class nav-tabs must have role="tablist"')
    if any(klass.startswith("alert-") for klass in classes):
        if (
            node.get("role") not in ("alert", "alertdialog", "status")
            and "alert-link" not in classes
        ):
            warnings.append(
                "An alert (class alert-*) must have an alert, alertdialog or "
                "status role or an alert-link class. Please use alert and "
                "alertdialog only for what expects to stop any activity to "
                "be read immediately."
            )
    if any(klass.startswith("fa-") for klass in classes):
        description = f"A <{node.tag}> with fa class ({expr})"
        warnings += get_fa_class_accessibility_warnings(node, description)
    if any(klass.startswith("btn") for klass in classes):
        if (
            node.tag in ("a", "button", "select")
            or (
                node.tag == "input"
                and node.get("type") in ("button", "submit", "reset")
            )
            or any(
                klass in classes for klass in ("btn-group", "btn-toolbar", "btn-addr")
            )
            or (node.tag == "field" and node.get("widget") == "url")
        ):
            pass
        else:
            warnings.append(
                "A simili button must be in tag a/button/select or tag `input` "
                "with type button/submit/reset or have class in "
                "btn-group/btn-toolbar/btn-addr"
            )
    return warnings
