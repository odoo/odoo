import argparse
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

RENAMES: dict[str, str] = {"t-esc": "t-out"}


def _rename(element: etree._Element) -> bool:
    if not RENAMES.keys() & element.attrib.keys():
        return False
    if any(RENAMES[old] in element.attrib for old in RENAMES if old in element.attrib):
        return False
    attribs = list(element.attrib.items())
    element.attrib.clear()
    for key, value in attribs:
        element.set(RENAMES.get(key, key), value)
    return True


def _shape(source: bytes, renames: dict[str, str]) -> list:
    root = etree.parse(BytesIO(source), _PARSER).getroot()
    out = []
    for element in root.iter():
        if callable(element.tag):
            out.append(("#comment", element.text))
            continue
        out.append(
            (
                element.tag,
                sorted((renames.get(k, k), v) for k, v in element.attrib.items()),
                (element.text or "").strip(),
                (element.tail or "").strip(),
            )
        )
    return out


def is_rename_only(source: bytes, rewritten: bytes) -> bool:
    try:
        return _shape(source, RENAMES) == _shape(rewritten, {})
    except etree.LxmlError:
        return False


def modernize_xml_file(path: Path, *, dry_run: bool = False) -> bool | None:
    source = path.read_bytes()
    try:
        tree = etree.parse(BytesIO(source), _PARSER)
    except etree.XMLSyntaxError as exc:
        _logger.warning("  SKIP  %s: %s", path, exc)
        return None

    changed = False
    for element in tree.getroot().iter():
        if not callable(element.tag) and _rename(element):
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

    if not is_rename_only(source, new_content):
        _logger.warning(
            "  SKIP  %s: the rewrite changes more than the directive names", path
        )
        return None

    if not dry_run:
        path.write_bytes(new_content)
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rename the deprecated t-esc output directive to t-out.",
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
            label = "would rename" if args.dry_run else "renamed     "
            print(f"  {label}  {xml_file}")  # noqa: T201, RUF100 CLI entry point: stdout is the fixer's report
            changed += 1
        else:
            unchanged += 1
    verb = "would change" if args.dry_run else "renamed"
    print(f"\nDone: {changed} {verb}, {unchanged} unchanged, {skipped} skipped")  # noqa: T201, RUF100 CLI entry point: stdout is the fixer's report


if __name__ == "__main__":
    main()
