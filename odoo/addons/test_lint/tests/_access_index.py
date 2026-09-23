import ast
import csv
import functools
import io
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

from odoo.modules import Manifest

from . import lint_case
from ._rules import is_test_path
from ._xml_identity import PARSER as _PARSER

_SKIP_DIRS = {"static", "node_modules", "_vendor", "migrations", "upgrades"}
_MODEL_BASES = {
    "Model": "model",
    "AbstractModel": "abstract",
    "TransientModel": "transient",
}
_MAGIC_FIELDS = {"id": None, "display_name": None}
_LOG_FIELDS = {
    "create_uid": "res.users",
    "create_date": None,
    "write_uid": "res.users",
    "write_date": None,
}
_RELATIONAL = {"Many2one", "One2many", "Many2many", "One2one"}
_LOGIC = frozenset({"&", "|", "!"})
OPERATORS = frozenset(
    {
        "=",
        "!=",
        "<=",
        "<",
        ">",
        ">=",
        "=?",
        "=like",
        "=ilike",
        "like",
        "not like",
        "ilike",
        "not ilike",
        "in",
        "not in",
        "child_of",
        "parent_of",
        "any",
        "not any",
        "any!",
        "not any!",
        "access",
        "starts with",
        "not starts with",
    }
)
OPERATIONS = {"c": "create", "r": "read", "u": "write", "d": "unlink"}


@dataclass
class FieldInfo:
    name: str
    type: str
    comodel: str | None = None
    related: str | None = None


@dataclass
class ModelInfo:
    name: str
    kind: str = "model"
    defined_in: str = ""
    module: str = ""
    inherit: list[str] = field(default_factory=list)
    inherits: dict[str, str] = field(default_factory=dict)
    fields: dict[str, FieldInfo] = field(default_factory=dict)
    log_access: bool = True
    inherits_rules: bool = True
    auto: bool = True


@dataclass
class Row:
    module: str
    xmlid: str
    path: str
    line: int
    model: str | None
    group: str | None
    kind: str | None
    operation: str | None
    domain: str | None
    creates: bool
    guard_scope: str | None = None

    def where(self) -> str:
        return f"{self.path}:{self.line} {self.xmlid}"


def _module_manifests() -> list:
    return [
        manifest
        for manifest in Manifest.get_all_addon_manifests()
        if lint_case.is_core_path(str(manifest.path))
    ]


def _walk(root: Path, suffix: str):
    for path in sorted(root.rglob(f"*{suffix}")):
        if _SKIP_DIRS.intersection(path.relative_to(root).parts):
            continue
        yield path


def _qualify(module: str, xmlid: str) -> str:
    return xmlid if "." in xmlid else f"{module}.{xmlid}"


def _model_of_ref(ref: str | None) -> str | None:
    if not ref:
        return None
    name = ref.split(".", 1)[-1]
    if not name.startswith("model_"):
        return None
    return name.removeprefix("model_")


def _csv_rows(module: str, path: Path) -> list[Row]:
    text = path.read_text(encoding="utf-8")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None) or []
    columns = [column.strip() for column in header]

    def column(names):
        return next((columns.index(name) for name in names if name in columns), None)

    at = {
        "id": column(("id",)),
        "model": column(("model_id/id", "model_id:id")),
        "group": column(("group_id/id", "group_id:id")),
        "kind": column(("kind",)),
        "operation": column(("operation",)),
        "domain": column(("domain",)),
        "guard_scope": column(("guard_scope",)),
    }
    rows = []
    for line, values in enumerate(reader, start=2):
        if not values or not any(values):
            continue

        def value(key, values=values):
            index = at[key]
            if index is None or index >= len(values):
                return None
            return values[index].strip() or None

        rows.append(
            Row(
                module=module,
                xmlid=_qualify(module, value("id") or f"#{line}"),
                path=str(path),
                line=line,
                model=_model_of_ref(value("model")),
                group=value("group"),
                kind=value("kind"),
                operation=value("operation"),
                domain=value("domain"),
                creates=True,
                guard_scope=value("guard_scope"),
            )
        )
    return rows


def _xml_rows(module: str, path: Path) -> list[Row]:
    try:
        root = etree.parse(str(path), _PARSER).getroot()
    except etree.XMLSyntaxError:
        return []
    rows = []
    for record in root.iter("record"):
        if record.get("model") != "ir.access":
            continue
        values = {}
        present = set()
        for element in record.iter("field"):
            name = element.get("name")
            present.add(name)
            values[name] = element.get("ref") or (element.text or "").strip() or None
        xmlid = _qualify(module, record.get("id") or f"#{record.sourceline}")
        rows.append(
            Row(
                module=module,
                xmlid=xmlid,
                path=str(path),
                line=record.sourceline,
                model=_model_of_ref(values.get("model_id")),
                group=values.get("group_id"),
                kind=values.get("kind"),
                operation=values.get("operation"),
                domain=values.get("domain"),
                creates=xmlid.startswith(f"{module}.") and "model_id" in present,
                guard_scope=values.get("guard_scope"),
            )
        )
    return rows


@functools.cache
def model_names_by_ref() -> dict[str, str]:
    return {name.replace(".", "_"): name for name in models()}


def _resolve(row: Row) -> Row:
    if row.model:
        row.model = model_names_by_ref().get(row.model, row.model)
    return row


@functools.cache
def rows() -> tuple[Row, ...]:
    return tuple(map(_resolve, _rows()))


def _rows() -> list[Row]:
    found: list[Row] = []
    for manifest in _module_manifests():
        root = Path(manifest.path)
        for path in _walk(root, ".csv"):
            if path.name == "ir.access.csv":
                found.extend(_csv_rows(manifest.name, path))
        for path in _walk(root, ".xml"):
            if "ir.access" in path.read_text(encoding="utf-8", errors="replace"):
                found.extend(_xml_rows(manifest.name, path))
    return found


def _string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _strings(node: ast.AST | None) -> list[str]:
    if (value := _string(node)) is not None:
        return [value]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [value for item in node.elts if (value := _string(item)) is not None]
    return []


def _base_names(class_node: ast.ClassDef) -> list[str]:
    return [
        base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
        for base in class_node.bases
    ]


def _field_of(name: str, call: ast.Call) -> FieldInfo | None:
    func = call.func
    if not (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "fields"
    ):
        return None
    kind = func.attr
    if not kind[:1].isupper():
        return None
    comodel = related = None
    if kind in _RELATIONAL:
        comodel = _string(call.args[0]) if call.args else None
        for keyword in call.keywords:
            if keyword.arg == "comodel_name":
                comodel = _string(keyword.value)
            elif keyword.arg == "related":
                related = _string(keyword.value)
    return FieldInfo(name, kind, comodel, related)


@dataclass
class _ClassDef:
    kind: str | None
    bases: list[str]
    pyname: str
    name: str | None
    inherit: list[str]
    inherits: dict[str, str]
    fields: dict[str, FieldInfo]
    attributes: dict[str, object]
    path: str
    module: str = ""


def _class_defs(path: Path) -> list[_ClassDef]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError, UnicodeDecodeError:
        return []
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or not node.bases:
            continue
        bases = _base_names(node)
        kind = next((_MODEL_BASES[b] for b in bases if b in _MODEL_BASES), None)
        name = None
        inherit: list[str] = []
        inherits: dict[str, str] = {}
        fields: dict[str, FieldInfo] = {}
        attributes: dict[str, object] = {}
        for statement in node.body:
            if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                continue
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
            )
            value = statement.value
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id == "_name":
                    name = _string(value)
                elif target.id == "_inherit":
                    inherit = _strings(value)
                elif target.id == "_inherits" and isinstance(value, ast.Dict):
                    inherits = {
                        key: field_name
                        for key_node, value_node in zip(
                            value.keys, value.values, strict=True
                        )
                        if (key := _string(key_node))
                        and (field_name := _string(value_node))
                    }
                elif target.id in ("_log_access", "_inherits_rules", "_auto"):
                    if isinstance(value, ast.Constant):
                        attributes[target.id] = value.value
                elif isinstance(value, ast.Call) and (
                    info := _field_of(target.id, value)
                ):
                    fields[target.id] = info
        if kind is None and not (name or inherit):
            continue
        found.append(
            _ClassDef(
                kind,
                bases,
                node.name,
                name,
                inherit,
                inherits,
                fields,
                attributes,
                str(path),
            )
        )
    return found


@functools.cache
def models() -> dict[str, ModelInfo]:
    definitions: defaultdict[str, list[_ClassDef]] = defaultdict(list)
    for manifest in _module_manifests():
        root = Path(manifest.path)
        for path in _walk(root, ".py"):
            if "tests" in path.relative_to(root).parts:
                continue
            for class_def in _class_defs(path):
                class_def.module = manifest.name
                name = class_def.name or (
                    class_def.inherit[0] if class_def.inherit else None
                )
                if name:
                    definitions[name].append(class_def)
    for path in lint_case.framework_paths():
        if is_test_path(path):
            continue
        for class_def in _class_defs(Path(path)):
            if class_def.name:
                definitions[class_def.name].append(class_def)

    kinds = {
        class_def.pyname: class_def.kind
        for class_defs in definitions.values()
        for class_def in class_defs
        if class_def.kind
    }
    for class_defs in definitions.values():
        for class_def in class_defs:
            if class_def.kind is None:
                class_def.kind = next(
                    (kinds[base] for base in class_def.bases if base in kinds),
                    "abstract",
                )
    result: dict[str, ModelInfo] = {}
    for name, class_defs in definitions.items():
        own = [class_def for class_def in class_defs if class_def.name == name]
        info = ModelInfo(name)
        if own:
            info.kind = own[0].kind
            info.defined_in = own[0].path
            info.module = own[0].module
        else:
            info.kind = "extension"
        for class_def in class_defs:
            for parent in class_def.inherit:
                if parent != name and parent not in info.inherit:
                    info.inherit.append(parent)
            info.inherits.update(class_def.inherits)
            for field_name, field_info in class_def.fields.items():
                known = info.fields.get(field_name)
                if known and known.comodel and not field_info.comodel:
                    continue
                info.fields[field_name] = field_info
            if class_def.attributes.get("_log_access") is False:
                info.log_access = False
            if class_def.attributes.get("_inherits_rules") is False:
                info.inherits_rules = False
            if class_def.attributes.get("_auto") is False:
                info.auto = False
        result[name] = info
    return result


@functools.cache
def fields_of(model_name: str) -> dict[str, FieldInfo]:
    return _fields_of(model_name, frozenset())


def _fields_of(model_name: str, seen: frozenset[str]) -> dict[str, FieldInfo]:
    info = models().get(model_name)
    result = {
        name: FieldInfo(name, "Many2one" if comodel else "Field", comodel)
        for name, comodel in _MAGIC_FIELDS.items()
    }
    if info is None or model_name in seen:
        return result
    seen |= {model_name}
    if info.log_access and info.kind != "abstract":
        result.update(
            {
                name: FieldInfo(name, "Many2one" if comodel else "Field", comodel)
                for name, comodel in _LOG_FIELDS.items()
            }
        )
    for parent in [*info.inherit, *info.inherits]:
        _merge(result, _fields_of(parent, seen))
    _merge(result, info.fields)
    for parent, field_name in info.inherits.items():
        result.setdefault(field_name, FieldInfo(field_name, "Many2one", parent))
    return result


def _merge(result: dict[str, FieldInfo], fields: dict[str, FieldInfo]) -> None:
    for name, info in fields.items():
        known = result.get(name)
        if known and known.comodel and not info.comodel:
            continue
        result[name] = info


def comodel_of(model_name: str, info: FieldInfo, depth: int = 0) -> str | None:
    if info.comodel or not info.related or depth > 8:
        return info.comodel
    owner = model_name
    target = None
    for part in info.related.split("."):
        target = fields_of(owner).get(part)
        if target is None:
            return None
        owner = comodel_of(owner, target, depth + 1)
        if owner is None:
            return None
    return owner


def known_model(model_name: str | None) -> bool:
    return bool(model_name) and model_name in models()


@dataclass
class Condition:
    path: str
    operator: str
    value: ast.AST


def parse_domain(text: str) -> ast.AST:
    return ast.parse(text.strip(), mode="eval").body


def conditions(node: ast.AST) -> tuple[list[Condition], list[str]]:
    # the conditions a domain states literally, and what makes it malformed;
    # a part built at evaluation time (a call, a name, a concatenation) is not
    # judged, only its literal parts are
    found: list[Condition] = []
    problems: list[str] = []
    if isinstance(node, ast.IfExp):
        for branch in (node.body, node.orelse):
            sub_found, sub_problems = conditions(branch)
            found += sub_found
            problems += sub_problems
        return found, problems
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        for side in (node.left, node.right):
            sub_found, sub_problems = conditions(side)
            found += sub_found
            problems += sub_problems
        return found, problems
    if not isinstance(node, (ast.List, ast.Tuple)):
        return found, problems
    for item in node.elts:
        if (text := _string(item)) is not None:
            if text not in _LOGIC:
                problems.append(f"{text!r} is not a domain operator")
            continue
        if isinstance(item, (ast.List, ast.Tuple)):
            if len(item.elts) != 3:
                problems.append(f"a condition of {len(item.elts)} items")
                continue
            left, operator, value = item.elts
            path = _string(left)
            operator_text = _string(operator)
            if isinstance(left, ast.Constant) and not isinstance(left.value, str):
                continue
            if path is None or operator_text is None:
                continue
            if operator_text.lower() not in OPERATORS:
                problems.append(f"{operator_text!r} is not an operator")
                continue
            found.append(Condition(path, operator_text.lower(), value))
    return found, problems


def validate(model_name: str, text: str) -> list[str]:
    try:
        node = parse_domain(text)
    except SyntaxError as error:
        return [f"does not parse: {error.msg}"]
    return _validate(model_name, node)


def _validate(model_name: str, node: ast.AST) -> list[str]:
    found, problems = conditions(node)
    for condition in found:
        owner = model_name
        parts = condition.path.split(".")
        target = None
        for index, part in enumerate(parts):
            if not known_model(owner):
                target = None
                break
            target = fields_of(owner).get(part)
            if target is None:
                problems.append(f"{owner} has no field {part!r} ({condition.path})")
                break
            comodel = comodel_of(owner, target)
            if index < len(parts) - 1:
                if not comodel:
                    if target.type not in _RELATIONAL:
                        problems.append(
                            f"{owner}.{part} is not relational ({condition.path})"
                        )
                    target = None
                    break
                owner = comodel
        if target is None:
            continue
        if condition.operator == "access":
            if len(parts) != 1 or not (part == "id" or target.type == "Many2one"):
                problems.append(
                    f"'access' takes a many2one or 'id' of the model, not "
                    f"{condition.path}"
                )
            elif _string(condition.value) not in OPERATIONS.values():
                problems.append(f"'access' takes an operation, not {condition.path}")
        elif condition.operator in ("any", "not any", "any!", "not any!") and (
            comodel := comodel_of(owner, target)
        ):
            problems += _validate(comodel, condition.value)
    return problems


def access_edges(row: Row) -> list[tuple[str, str]]:
    # the (model, operation) the row's 'access' conditions make its own depend on
    if not row.domain or "access" not in row.domain or not known_model(row.model):
        return []
    try:
        found, _problems = conditions(parse_domain(row.domain))
    except SyntaxError:
        return []
    edges = []
    for condition in found:
        if condition.operator != "access" or "." in condition.path:
            continue
        operation = _string(condition.value)
        if condition.path == "id":
            edges.append((row.model, operation))
        elif (target := fields_of(row.model).get(condition.path)) and (
            comodel := comodel_of(row.model, target)
        ):
            edges.append((comodel, operation))
    return edges
