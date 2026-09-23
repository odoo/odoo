import argparse
import ast
import logging
import re
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

_DATA_ROOTS = frozenset({"odoo", "data"})

_TRUE = frozenset({"1", "True", "true"})


def is_menu_file(relative: str) -> bool:
    return "menu" in Path(relative).stem


def _manifest(module: Path) -> dict | None:
    try:
        return ast.literal_eval(
            (module / "__manifest__.py").read_text(encoding="utf-8")
        )
    except OSError, SyntaxError, ValueError:
        return None


def _noupdate(element: etree._Element) -> bool:
    return any(
        (ancestor.get("noupdate") or "").strip() in _TRUE
        for ancestor in element.iterancestors()
    )


def _top_level_menuitems(root: etree._Element) -> list[etree._Element]:
    found = []
    for element in root.iter("menuitem"):
        if callable(element.tag):
            continue
        parent = element.getparent()
        if parent is not None and parent.tag in _DATA_ROOTS:
            found.append(element)
    return found


def _with_preceding_comments(element: etree._Element) -> list[etree._Element]:
    group = [element]
    sibling = element.getprevious()
    while sibling is not None and callable(sibling.tag):
        group.insert(0, sibling)
        sibling = sibling.getprevious()
    return group


def _write(path: Path, tree: etree._ElementTree, had_decl: bool) -> None:
    buf = BytesIO()
    tree.write(buf, xml_declaration=False, encoding="utf-8", pretty_print=False)
    body = buf.getvalue()
    content = (_XML_DECL + b"\n" + body) if had_decl else body
    if not content.endswith(b"\n"):
        content += b"\n"
    path.write_bytes(content)


def _references(texts: list[str], module: str, moved: set[str]) -> set[str]:
    pattern = re.compile(
        r"""(?:ref\(\s*['"]|ref=["']|parent=["']|action=["']|id=["']|%\()(?:{module}\.)?({ids})(?=['"\)])""".format(
            module=re.escape(module), ids="|".join(map(re.escape, sorted(moved)))
        )
    )
    hits: set[str] = set()
    for text in texts:
        hits.update(pattern.findall(text))
    return hits


def _has_elements(root: etree._Element) -> bool:
    return any(not callable(child.tag) for child in root.iter() if child is not root)


def _record_ids(root: etree._Element) -> set[str]:
    return {
        element.get("id")
        for element in root.iter("record", "template", "menuitem")
        if not callable(element.tag) and element.get("id")
    }


def _action_refs(menus: list[etree._Element], module: str) -> set[str]:
    refs = set()
    for menu in menus:
        for element in menu.iter("menuitem"):
            if callable(element.tag):
                continue
            action = element.get("action") or ""
            if action and ("." not in action or action.startswith(module + ".")):
                refs.add(action.removeprefix(module + "."))
    return refs


def relocate_module(
    module: Path, *, dry_run: bool = False, python_refs_verified: bool = False
) -> tuple[bool, str | None]:
    manifest = _manifest(module)
    if manifest is None:
        return False, None
    data = list(manifest.get("data") or [])
    trees: dict[str, etree._ElementTree] = {}
    for relative in data:
        path = module / relative
        if path.suffix == ".xml" and path.is_file():
            try:
                trees[relative] = etree.parse(str(path), _PARSER)
            except etree.XMLSyntaxError:
                continue
    menus_by_file = {
        relative: _top_level_menuitems(tree.getroot())
        for relative, tree in trees.items()
        if not is_menu_file(relative)
    }
    menus_by_file = {r: m for r, m in menus_by_file.items() if m}
    if not menus_by_file:
        return False, None

    moved = [m for menus in menus_by_file.values() for m in menus]
    if any(_noupdate(m) for m in moved):
        return False, f"{module.name}: a menuitem sits under noupdate; move it by hand"
    if not all(m.get("id") for m in moved):
        return False, f"{module.name}: a menuitem has no id"
    moved_ids = {m.get("id") for m in moved}

    canonical = f"views/{module.name}_menus.xml"
    menu_files = [
        r
        for r in data
        if is_menu_file(r)
        and r in trees
        and (r == canonical or _top_level_menuitems(trees[r].getroot()))
    ]
    if menu_files:
        target_relative = menu_files[-1]
        target_tree = trees[target_relative]
        target_had_decl = (
            (module / target_relative).read_bytes().lstrip().startswith(b"<?xml")
        )
    else:
        target_relative = canonical
        if (module / target_relative).exists():
            return False, f"{module.name}: {target_relative} exists but is not listed"
        target_tree = etree.ElementTree(etree.Element("odoo"))
        target_had_decl = True
    target_root = target_tree.getroot()
    if target_root.tag != "odoo" or _noupdate(target_root):
        return False, f"{module.name}: {target_relative} is not a plain <odoo> file"

    ordered: list[etree._Element] = []
    existing = list(target_root)
    for relative in data:
        if relative == target_relative:
            ordered.extend(existing)
        elif relative in menus_by_file:
            for menu in menus_by_file[relative]:
                ordered.extend(_with_preceding_comments(menu))
    for element in ordered:
        target_root.append(element)

    staying = [r for r in data if r != target_relative]
    texts = {
        r: etree.tostring(trees[r], encoding="unicode")
        if r in trees
        else (module / r).read_text(encoding="utf-8")
        for r in staying
        if (module / r).is_file()
    }
    guarded = moved_ids | {
        m.get("id") for m in _top_level_menuitems(target_root) if m.get("id")
    }
    python = [
        path.read_text(encoding="utf-8")
        for path in module.rglob("*.py")
        if "tests" not in path.parts and "static" not in path.parts
    ]
    if not python_refs_verified and (used := _references(python, module.name, guarded)):
        why = f"{module.name}: Python references {sorted(used)}"
        return False, f"{why}; verify none runs at load, then --python-refs-verified"
    needs_menus = [
        r for r in staying if _references([texts.get(r, "")], module.name, guarded)
    ]
    position = staying.index(needs_menus[0]) if needs_menus else len(staying)
    defined_before = set()
    for r in staying[:position]:
        if r in trees:
            defined_before |= _record_ids(trees[r].getroot())
    if missing := _action_refs(moved, module.name) - defined_before - moved_ids:
        why = f"{module.name}: {sorted(missing)} would load after the menus file"
        return False, f"{why} ({needs_menus[0]} needs the menus first)"

    emptied = [r for r in menus_by_file if not _has_elements(trees[r].getroot())]
    new_data = [r for r in staying if r not in emptied]
    insert_at = len([r for r in staying[:position] if r not in emptied])
    new_data.insert(insert_at, target_relative)
    if dry_run:
        return True, None

    for relative in menus_by_file:
        if relative in emptied:
            (module / relative).unlink()
        else:
            path = module / relative
            _write(
                path, trees[relative], path.read_bytes().lstrip().startswith(b"<?xml")
            )
    (module / target_relative).parent.mkdir(parents=True, exist_ok=True)
    _write(module / target_relative, target_tree, target_had_decl)
    _rewrite_manifest_data(module / "__manifest__.py", data, new_data)
    return True, None


def _rewrite_manifest_data(path: Path, old: list[str], new: list[str]) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    literal = next(
        node.value
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Dict)
    )
    value = next(
        (
            value
            for key, value in zip(literal.keys, literal.values, strict=True)
            if isinstance(key, ast.Constant) and key.value == "data"
        ),
        None,
    )
    if value is None:
        raise ValueError(f"{path}: no data key")
    lines = source.split("\n")
    start, end = value.lineno - 1, value.end_lineno
    indent = re.match(r"\s*", lines[start]).group(0)
    inner = indent + "    "
    rendered = ["["] + [f'{inner}"{item}",' for item in new] + [f"{indent}]"]
    head = lines[start][: value.col_offset]
    tail = lines[end - 1][value.end_col_offset :]
    rendered[0] = head + rendered[0]
    rendered[-1] += tail
    lines[start:end] = rendered
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Move every top-level <menuitem> of a module into views/<module>_menus.xml, "
            "listed last in the manifest so every action it names exists first."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "roots",
        nargs="*",
        metavar="DIR",
        default=["."],
        help="Addons directories to walk (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Print which modules would change without modifying them",
    )
    parser.add_argument(
        "--python-refs-verified",
        metavar="MODULE",
        action="append",
        default=[],
        help=(
            "A module whose Python references to its menus were read and none runs "
            "while data loads; the fixer then places the file by the data files alone"
        ),
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
    for root in args.roots:
        for module in sorted(Path(root).iterdir()):
            if (
                module.name in args.exclude
                or not (module / "__manifest__.py").is_file()
            ):
                continue
            result, why = relocate_module(
                module,
                dry_run=args.dry_run,
                python_refs_verified=module.name in args.python_refs_verified,
            )
            if why:
                _logger.warning("  SKIP  %s", why)
                skipped += 1
            elif result:
                label = "would move" if args.dry_run else "moved     "
                print(f"  {label}  {module.name}")  # noqa: T201, RUF100 CLI entry point: stdout is the fixer's report
                changed += 1
            else:
                unchanged += 1
    verb = "would change" if args.dry_run else "changed"
    print(f"\nDone: {changed} {verb}, {unchanged} unchanged, {skipped} skipped")  # noqa: T201, RUF100 CLI entry point: stdout is the fixer's report


if __name__ == "__main__":
    main()
