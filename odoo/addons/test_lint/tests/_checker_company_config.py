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
    # a class that inherits res.company extends it, whether or not it also
    # restates `_name`; base's own definition names no `_inherit`
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
    return False


def _is_field(value: ast.expr) -> bool:
    match value:
        case ast.Call(func=ast.Attribute(value=ast.Name(id="fields"))):
            return True
    return False


def _is_related_through_config(value: ast.expr) -> bool:
    # a related through `<app>_config_id` declares no storage and no logic
    # on the tenant: it is the configuration read from a company view
    match value:
        case ast.Call(keywords=keywords):
            for keyword in keywords:
                match keyword:
                    case ast.keyword(
                        arg="related", value=ast.Constant(value=str() as path)
                    ):
                        head, _sep, _rest = path.partition(".")
                        return head.endswith("_config_id")
    return False


def _is_company_owned_collection(value: ast.expr) -> bool:
    match value:
        case ast.Call(func=ast.Attribute(attr="One2many"), keywords=keywords):
            return any(keyword.arg == "inverse_name" for keyword in keywords)
    return False


def _reads_without_writing(value: ast.expr) -> bool:
    # a derivation that declares neither `store=True` nor an `inverse` holds
    # nothing on the company and writes nothing through it: it is a view of
    # data that already lives somewhere, and a view has no place to move to.
    # `related=` is the same thing spelled shorter
    match value:
        case ast.Call(keywords=keywords):
            derives = False
            for keyword in keywords:
                match keyword:
                    case ast.keyword(arg="inverse"):
                        return False
                    case ast.keyword(arg="store", value=ast.Constant(value=True)):
                        return False
                    case ast.keyword(arg="store"):
                        # anything but a literal True is not readable here, so
                        # the field is judged as though it stored
                        return False
                    case ast.keyword(arg="compute" | "related"):
                        derives = True
            return derives
    return False


def _credential_holder_link(class_node: ast.ClassDef) -> str | None:
    # the link to the company's vault is `<app>_config_id`'s sibling: a
    # contract `mixin.credential.holder` names, not a setting of its own
    for statement in class_node.body:
        match statement:
            case ast.Assign(
                targets=[ast.Name(id="_credential_holder_field")],
                value=ast.Constant(value=str() as name),
            ):
                return name
    return None


def _credential_doors(class_node: ast.ClassDef) -> set[str]:
    # a credential door is not storage: the secret rests in the vault, and the
    # company declares a compute/inverse pair so a settings view can read and
    # write it there. Moving the door to a configuration would move the door
    # and not the secret, which is already somewhere neither one of them is
    for statement in class_node.body:
        match statement:
            case ast.Assign(
                targets=[ast.Name(id="_CREDENTIAL_FIELDS")], value=ast.Dict(keys=keys)
            ):
                return {
                    key.value
                    for key in keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
    return set()


def check(tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or not _extends_company(node):
            continue
        doors = _credential_doors(node)
        vault_link = _credential_holder_link(node)
        for statement in node.body:
            # a type annotation is a spelling of the same declaration, so both
            # forms are read here: matching only `ast.Assign` let an annotated
            # field declare a setting on the company that no gate could see
            match statement:
                case (
                    ast.Assign(targets=[ast.Name(id=name)], value=value)
                    | ast.AnnAssign(target=ast.Name(id=name), value=value)
                ) if (
                    value is not None
                    and _is_field(value)
                    and not name.endswith("_config_id")
                    and not _is_related_through_config(value)
                    and not _is_company_owned_collection(value)
                    and not _reads_without_writing(value)
                    and name not in doors
                    and name != vault_link
                ):
                    yield Violation(
                        statement.lineno,
                        statement.col_offset,
                        f"res.company.{name} belongs to the application's "
                        f"mixin.company.config model, linked through <app>_config_id",
                    )
