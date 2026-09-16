import argparse
import ast
import json
import sys
from pathlib import Path

MANIFEST_KEY_ORDER: list[str] = [
    "name",
    "version",
    "category",
    "sequence",
    "summary",
    "description",
    "author",
    "contributors",
    "maintainer",
    "maintainers",
    "website",
    "url",
    "support",
    "live_test_url",
    "price",
    "currency",
    "icon",
    "images",
    "images_preview_theme",
    "license",
    "depends",
    "external_dependencies",
    "countries",
    "data",
    "demo",
    "oca_data_manual",
    "assets",
    "esm",
    "bootstrap",
    "web",
    "configurator_snippets",
    "configurator_snippets_addons",
    "new_page_templates",
    "theme_customizations",
    "iot_handlers_in_image",
    "cloc_exclude",
    "installable",
    "application",
    "auto_install",
    "post_load",
    "pre_init_hook",
    "post_init_hook",
    "uninstall_hook",
]

DEPRECATED_KEYS: dict[str, str] = {
    "init_xml": "data",
    "update_xml": "data",
    "demo_xml": "demo",
    "test": "",
}

KEPT_DEFAULTS = frozenset({"version"})

_KEY_RANK: dict[str, int] = {k: i for i, k in enumerate(MANIFEST_KEY_ORDER)}

_INDENT = "    "

_DROP = object()


def expected_key_order(present_keys: list[str]) -> list[str]:
    known = [k for k in MANIFEST_KEY_ORDER if k in present_keys]
    unknown = sorted(k for k in present_keys if k not in _KEY_RANK)
    return known + unknown


def default_icon(module: str) -> str:
    return f"/{module}/static/description/icon.png"


def _normalize_value(module: str, key: str, value: object) -> object:
    match key, value:
        case "icon", str() if value.strip() == default_icon(module):
            return _DROP
        case (
            (
                "name"
                | "category"
                | "author"
                | "license"
                | "website"
                | "url"
                | "support"
                | "live_test_url"
                | "icon"
            ),
            str(),
        ):
            return value.strip()
        case "summary", str():
            return " ".join(value.split())
        case (("description" | "website"), str()) if not value.strip():
            return ""
        case "countries", list():
            return [c.lower() if isinstance(c, str) else c for c in value]
        case "assets", dict():
            return {
                bundle: sorted(entries)
                if isinstance(entries, (set, frozenset))
                else list(entries)
                if isinstance(entries, tuple)
                else entries
                for bundle, entries in value.items()
            }
        case _:
            return value


def normalize(module: str, data: dict) -> dict:
    from odoo.modules.module import _DEFAULT_MANIFEST

    kept = {}
    for key, value in data.items():
        value = _normalize_value(module, key, value)
        if value is _DROP:
            continue
        if (
            key in _DEFAULT_MANIFEST
            and key not in KEPT_DEFAULTS
            and type(value) is type(_DEFAULT_MANIFEST[key])
            and value == _DEFAULT_MANIFEST[key]
        ):
            continue
        kept[key] = value
    return {key: kept[key] for key in expected_key_order(list(kept))}


def _fmt_str(s: str) -> str:
    if "\n" in s:
        candidate = f'"""{s.replace("\\", "\\\\").replace('"""', r"\"\"\"")}"""'
        try:
            if ast.literal_eval(candidate) == s:
                return candidate
        except SyntaxError, ValueError:
            pass
    try:
        s.encode("utf-8")
    except UnicodeEncodeError:
        return json.dumps(s)
    if '"' in s and "'" not in s and s.isprintable():
        # the quote that needs no escape, which is what ruff format leaves
        return "'" + s.replace("\\", "\\\\") + "'"
    return json.dumps(s, ensure_ascii=False)


def _fmt_value(value: object, depth: int) -> str:
    pad = _INDENT * depth
    inner = _INDENT * (depth + 1)

    match value:
        case bool():
            return "True" if value else "False"
        case int():
            return str(value)
        case str():
            return _fmt_str(value)
        case None:
            return "None"
        case list():
            if not value:
                return "[]"
            items = "\n".join(f"{inner}{_fmt_value(v, depth + 1)}," for v in value)
            return f"[\n{items}\n{pad}]"
        case tuple():
            if not value:
                return "()"
            items = "\n".join(f"{inner}{_fmt_value(v, depth + 1)}," for v in value)
            return f"(\n{items}\n{pad})"
        case dict():
            if not value:
                return "{}"
            lines = "\n".join(
                f"{inner}{_fmt_str(k)}: {_fmt_value(v, depth + 1)},"
                for k, v in value.items()
            )
            return f"{{\n{lines}\n{pad}}}"
        case _:
            return repr(value)


def render_manifest(data: dict) -> str:
    body = "\n".join(f'{_INDENT}"{k}": {_fmt_value(v, 1)},' for k, v in data.items())
    return f"{{\n{body}\n}}\n"


def _dict_literal(tree: ast.Module) -> ast.Dict | None:
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Dict):
            return node.value
    return None


def _is_faithful(new_source: str, data: dict) -> bool:
    try:
        node = _dict_literal(ast.parse(new_source))
    except SyntaxError:
        return False
    if node is None:
        return False
    try:
        return ast.literal_eval(node) == data
    except ValueError, TypeError:
        return False


def read_manifest(path: Path) -> dict | None:
    try:
        node = _dict_literal(ast.parse(path.read_text(encoding="utf-8")))
        data = ast.literal_eval(node) if node is not None else None
    except SyntaxError, ValueError, TypeError:
        return None
    return data if isinstance(data, dict) else None


def sort_manifest(path: Path, *, dry_run: bool = False) -> bool | None:
    source = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print(f"  SKIP  {path}: syntax error — {exc}", file=sys.stderr)
        return None

    dict_node = _dict_literal(tree)
    if dict_node is None:
        print(f"  SKIP  {path}: no top-level dict literal found", file=sys.stderr)
        return None

    try:
        data = ast.literal_eval(dict_node)
    except (ValueError, TypeError) as exc:
        print(f"  SKIP  {path}: cannot evaluate dict — {exc}", file=sys.stderr)
        return None

    if not isinstance(data, dict):
        print(f"  SKIP  {path}: top-level literal is not a dict", file=sys.stderr)
        return None

    expected = normalize(path.parent.name, data)

    source_lines = source.splitlines(keepends=True)
    prefix = "".join(source_lines[: dict_node.lineno - 1]).lstrip("\n")
    assert dict_node.end_lineno is not None
    assert dict_node.end_col_offset is not None
    same_line_tail = source_lines[dict_node.end_lineno - 1][dict_node.end_col_offset :]
    suffix = "".join(source_lines[dict_node.end_lineno :])

    rendered = render_manifest(expected)
    if same_line_tail.strip():
        rendered = rendered.rstrip("\n") + same_line_tail
    new_source = prefix + rendered + suffix

    if new_source == source:
        return False

    if not _is_faithful(new_source, expected):
        print(
            f"  SKIP  {path}: the rewritten manifest would not say the same thing",
            file=sys.stderr,
        )
        return None

    if not dry_run:
        path.write_text(new_source, encoding="utf-8")
    return True


def iter_manifests(roots: list[str], excluded: set[str]):
    for root in roots:
        for manifest in sorted(Path(root).rglob("__manifest__.py")):
            if not excluded.intersection(manifest.parts):
                yield manifest


def ensure_odoo_importable() -> None:
    try:
        import odoo.modules.module  # noqa: F401 -- probing importability
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[4]))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rewrite Odoo __manifest__.py files into canonical shape: keys in "
            "canonical order, defaults dropped, values normalised."
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
        default=["_vendor", "node_modules"],
        help="Directory names to skip (default: _vendor, node_modules); repeatable",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ensure_odoo_importable()

    changed = unchanged = skipped = 0

    for manifest in iter_manifests(args.roots, set(args.exclude)):
        result = sort_manifest(manifest, dry_run=args.dry_run)
        if result is None:
            skipped += 1
        elif result:
            label = "would rewrite" if args.dry_run else "rewrote      "
            print(f"  {label}  {manifest}")
            changed += 1
        else:
            unchanged += 1

    verb = "would change" if args.dry_run else "rewrote"
    print(f"\nDone: {changed} {verb}, {unchanged} unchanged, {skipped} skipped")
    return 1 if skipped or (args.dry_run and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
