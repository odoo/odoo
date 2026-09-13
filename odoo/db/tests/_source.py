import ast
import inspect
import textwrap


def _callees(func) -> set[str]:
    return set(inspect.unwrap(func).__code__.co_names)


def _def_ast(source: str) -> ast.FunctionDef | ast.ClassDef:
    node = ast.parse(textwrap.dedent(source)).body[0]
    if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        raise TypeError(f"expected a def or a class, parsed {type(node).__name__}")
    return node


def _calls_on(func, receiver: str) -> set[str]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if (
            isinstance(owner, ast.Attribute)
            and owner.attr == receiver
            and isinstance(owner.value, ast.Name)
            and owner.value.id == "self"
        ):
            found.add(node.func.attr)
    return found


def _instance_attrs(cls) -> set[str]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(cls)))
    found = set()
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for t in targets:
            if (
                isinstance(t, ast.Attribute)
                and isinstance(t.value, ast.Name)
                and t.value.id == "self"
            ):
                found.add(t.attr)
    return found
