import argparse
import ast
import logging
from io import BytesIO
from pathlib import Path

from lxml import etree

_logger = logging.getLogger(__name__)

try:
    from . import _pretty_xml
except ImportError:
    import _pretty_xml

_PARSER = etree.XMLParser(remove_comments=False, strip_cdata=False)

_XML_DECL = b'<?xml version="1.0" encoding="utf-8"?>'

_COMMAND_TAGS = frozenset({"field", "value"})

_BY_CODE: dict[int, tuple[str, int]] = {
    0: ("create", 3),
    1: ("update", 3),
    2: ("delete", 2),
    3: ("unlink", 2),
    4: ("link", 2),
    5: ("clear", 3),
    6: ("set", 3),
}

_BY_NAME: dict[str, int] = {name: code for code, (name, _) in _BY_CODE.items()}


def _is_command_tuple(node: ast.AST) -> bool:
    if not isinstance(node, ast.Tuple) or not node.elts:
        return False
    code = node.elts[0]
    if not (isinstance(code, ast.Constant) and code.value in _BY_CODE):
        return False
    if code.value == 5:
        return len(node.elts) <= 3
    arity = _BY_CODE[code.value][1]
    if len(node.elts) == 3 and arity == 2:
        third = node.elts[2]
        if not (isinstance(third, ast.Constant) and third.value == 0):
            return False
    elif len(node.elts) != arity:
        return False
    second = node.elts[1]
    return (isinstance(second, ast.Constant) and second.value == 0) or isinstance(
        second, (ast.Call, ast.Name, ast.Attribute)
    )


def _call(name: str, args: list[ast.expr]) -> ast.Call:
    return ast.Call(
        func=ast.Attribute(
            value=ast.Name(id="Command", ctx=ast.Load()), attr=name, ctx=ast.Load()
        ),
        args=args,
        keywords=[],
    )


def _to_command(node: ast.Tuple) -> ast.Call:
    code = node.elts[0].value
    name, _ = _BY_CODE[code]
    match name:
        case "create" | "set":
            return _call(name, [node.elts[2]])
        case "update":
            return _call(name, [node.elts[1], node.elts[2]])
        case "delete" | "unlink" | "link":
            return _call(name, [node.elts[1]])
        case _:
            return _call("clear", [])


def _rewrite_list(node: ast.List) -> bool:
    changed = False
    for index, element in enumerate(node.elts):
        if not _is_command_tuple(element):
            continue
        call = _to_command(element)
        vals = call.args[-1] if call.func.attr in ("create", "update") else None
        if isinstance(vals, ast.Dict):
            for value in vals.values:
                if isinstance(value, ast.List):
                    _rewrite_list(value)
        node.elts[index] = call
        changed = True
    return changed


def modernize(expression: str) -> str | None:
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError:
        return None
    if not isinstance(tree.body, ast.List) or not _rewrite_list(tree.body):
        return None
    return ast.unparse(tree)


class _ToTuples(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "Command"
            and func.attr in _BY_NAME
            and not node.keywords
        ):
            code = ast.Constant(_BY_NAME[func.attr])
            zero = ast.Constant(0)
            match func.attr:
                case "create" | "set":
                    return ast.Tuple(elts=[code, zero, *node.args], ctx=ast.Load())
                case "update":
                    return ast.Tuple(elts=[code, *node.args], ctx=ast.Load())
                case "clear":
                    return ast.Tuple(elts=[code, zero, zero], ctx=ast.Load())
                case _:
                    return ast.Tuple(elts=[code, *node.args, zero], ctx=ast.Load())
        return node


class _Normalise(ast.NodeTransformer):
    def visit_Tuple(self, node: ast.Tuple) -> ast.AST:
        self.generic_visit(node)
        if _is_command_tuple(node):
            code = node.elts[0].value
            zero = ast.Constant(0)
            if code == 5:
                return ast.Tuple(elts=[node.elts[0], zero, zero], ctx=ast.Load())
            if len(node.elts) == 2:
                return ast.Tuple(elts=[*node.elts, zero], ctx=ast.Load())
            if _BY_CODE[code][1] == 2:
                return ast.Tuple(elts=[*node.elts[:2], zero], ctx=ast.Load())
        return node


def _as_tuples(expression: str) -> str:
    tree = ast.parse(expression.strip(), mode="eval")
    return ast.dump(_Normalise().visit(_ToTuples().visit(tree)))


def is_equivalent(original: str, rewritten: str) -> bool:
    try:
        return _as_tuples(original) == _as_tuples(rewritten)
    except SyntaxError:
        return False


def modernize_xml_file(path: Path, *, dry_run: bool = False) -> bool | None:
    source = path.read_bytes()
    try:
        tree = etree.parse(BytesIO(source), _PARSER)
    except etree.XMLSyntaxError as exc:
        _logger.warning("  SKIP  %s: %s", path, exc)
        return None

    changed = False
    for element in tree.getroot().iter(*_COMMAND_TAGS):
        if callable(element.tag):
            continue
        expression = element.get("eval")
        if not expression or "(" not in expression:
            continue
        rewritten = modernize(expression)
        if rewritten is None:
            continue
        if not is_equivalent(expression, rewritten):
            _logger.warning(
                "  SKIP  %s:%s: the rewrite of %r would not say the same thing",
                path,
                element.sourceline,
                expression,
            )
            return None
        element.set("eval", rewritten)
        changed = True

    if not changed:
        return False

    buf = BytesIO()
    tree.write(buf, xml_declaration=False, encoding="utf-8", pretty_print=False)
    body = buf.getvalue()
    had_decl = source.lstrip().startswith(b"<?xml")
    new_content = (_XML_DECL + b"\n" + body) if had_decl else body
    if source.endswith(b"\n") and not new_content.endswith(b"\n"):
        new_content += b"\n"

    if not dry_run:
        path.write_bytes(new_content)
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rewrite the (code, id, values) x2many command tuples in eval= "
            "attributes as Command.create/update/delete/unlink/link/clear/set."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "roots",
        nargs="*",
        metavar="DIR",
        default=["."],
        help="Directories to search recursively (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Print which files would change without modifying them",
    )
    parser.add_argument(
        "--exclude",
        metavar="DIR",
        action="append",
        default=[],
        help=(
            "Extra directory names to skip, on top of the always-excluded "
            f"{', '.join(sorted(_pretty_xml.EXCLUDED_DIRS))}; repeatable"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    changed = unchanged = skipped = 0
    for xml_file in _pretty_xml.iter_target_files(args.roots, set(args.exclude)):
        result = modernize_xml_file(xml_file, dry_run=args.dry_run)
        if result is None:
            skipped += 1
        elif result:
            label = "would rewrite" if args.dry_run else "rewrote      "
            print(f"  {label}  {xml_file}")  # noqa: T201, RUF100 CLI entry point: stdout is the fixer's report
            changed += 1
        else:
            unchanged += 1
    verb = "would change" if args.dry_run else "rewritten"
    print(f"\nDone: {changed} {verb}, {unchanged} unchanged, {skipped} skipped")  # noqa: T201, RUF100 CLI entry point: stdout is the fixer's report


if __name__ == "__main__":
    main()
