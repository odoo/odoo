import ast
from collections.abc import Iterator
from dataclasses import dataclass

# An application keeps what it configures per company on its own
# `mixin.company.config` model and links it from the company through one
# `<app>_config_id` field: the tenant carries its identity and tenancy, not
# every application's settings.


@dataclass
class Violation:
    lineno: int
    col_offset: int
    message: str


def _extends_company(class_node: ast.ClassDef) -> bool:
    for statement in class_node.body:
        match statement:
            case ast.Assign(targets=[ast.Name(id="_inherit")], value=value):
                match value:
                    case ast.Constant(value="res.company"):
                        return True
                    case ast.List(elts=elts) | ast.Tuple(elts=elts):
                        return any(
                            isinstance(elt, ast.Constant) and elt.value == "res.company"
                            for elt in elts
                        )
            case ast.Assign(
                targets=[ast.Name(id="_name")], value=ast.Constant(value="res.company")
            ):
                return False
    return False


def _is_field(value: ast.expr) -> bool:
    match value:
        case ast.Call(func=ast.Attribute(value=ast.Name(id="fields"))):
            return True
    return False


def check(tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or not _extends_company(node):
            continue
        for statement in node.body:
            match statement:
                case ast.Assign(targets=[ast.Name(id=name)], value=value) if _is_field(
                    value
                ) and not name.endswith("_config_id"):
                    yield Violation(
                        statement.lineno,
                        statement.col_offset,
                        f"res.company.{name} belongs to the application's "
                        f"mixin.company.config model, linked through <app>_config_id",
                    )
