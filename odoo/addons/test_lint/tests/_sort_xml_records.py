import argparse
import sys
from collections import Counter
from io import BytesIO
from pathlib import Path

from lxml import etree

try:
    from ._xml_identity import preserves_content
except ImportError:
    from _xml_identity import preserves_content

try:
    from . import _pretty_xml
except ImportError:
    import _pretty_xml

FIELD_ORDER: dict[str, list[str]] = {
    "ir.ui.view": [
        "name",
        "key",
        "model",
        "inherit_id",
        "mode",
        "priority",
        "type",
        "group_ids",
        "active",
        "arch",
    ],
    "ir.actions.act_window": [
        "name",
        "res_model",
        "path",
        "view_mode",
        "view_id",
        "search_view_id",
        "target",
        "domain",
        "context",
        "limit",
        "binding_model_id",
        "binding_type",
        "binding_view_types",
        "binding_sequence",
        "binding_icon",
        "group_ids",
        "usage",
        "help",
    ],
    "ir.actions.act_window.view": [
        "sequence",
        "view_mode",
        "view_id",
        "act_window_id",
    ],
    "ir.actions.server": [
        "name",
        "model_id",
        "binding_model_id",
        "binding_type",
        "binding_view_types",
        "binding_sequence",
        "binding_icon",
        "group_ids",
        "usage",
        "state",
        "child_ids",
        "update_path",
        "value",
        "resource_ref",
        "code",
    ],
    "ir.actions.report": [
        "name",
        "model",
        "report_type",
        "report_name",
        "report_file",
        "print_report_name",
        "multi",
        "paperformat_id",
        "attachment",
        "attachment_use",
        "domain",
        "binding_model_id",
        "binding_type",
        "binding_view_types",
        "binding_sequence",
        "binding_icon",
        "group_ids",
    ],
    "ir.actions.client": [
        "name",
        "res_model",
        "tag",
        "target",
        "context",
        "params",
        "path",
    ],
    "ir.actions.act_url": [
        "name",
        "url",
        "target",
    ],
    "ir.actions.todo": [
        "name",
        "action_id",
        "sequence",
        "state",
    ],
    "ir.rule": [
        "name",
        "model_id",
        "global",
        "active",
        "domain_force",
        "groups",
        "perm_read",
        "perm_write",
        "perm_create",
        "perm_unlink",
    ],
    "ir.model.access": [
        "name",
        "model_id",
        "group_id",
        "active",
        "perm_read",
        "perm_write",
        "perm_create",
        "perm_unlink",
    ],
    "ir.cron": [
        "name",
        "model_id",
        "state",
        "code",
        "user_id",
        "repeat_interval",
        "repeat_unit",
        "nextcall",
        "priority",
        "active",
    ],
    "ir.config_parameter": [
        "key",
        "value",
    ],
    "ir.sequence": [
        "name",
        "code",
        "implementation",
        "prefix",
        "suffix",
        "padding",
        "number_next",
        "number_increment",
        "use_date_range",
        "company_id",
    ],
    "ir.module.category": [
        "name",
        "description",
        "parent_id",
        "sequence",
        "exclusive",
        "visible",
    ],
    "ir.filters": [
        "name",
        "model_id",
        "user_ids",
        "action_id",
        "domain",
        "context",
        "sort",
        "is_default",
    ],
    "ir.ui.menu": [
        "name",
        "parent_id",
        "action",
        "sequence",
        "group_ids",
        "web_icon",
        "active",
    ],
    "ir.asset": [
        "name",
        "bundle",
        "directive",
        "path",
        "target",
        "sequence",
        "active",
    ],
    "report.paperformat": [
        "name",
        "format",
        "page_height",
        "page_width",
        "orientation",
        "margin_top",
        "margin_bottom",
        "margin_left",
        "margin_right",
        "header_line",
        "header_spacing",
        "dpi",
        "css_margins",
        "disable_shrinking",
    ],
    "res.groups": [
        "name",
        "sequence",
        "privilege_id",
        "comment",
        "implied_ids",
        "implied_by_ids",
        "user_ids",
        "api_key_duration",
    ],
    "res.users": [
        "name",
        "login",
        "password",
        "partner_id",
        "company_id",
        "company_ids",
        "email",
        "signature",
        "image_1920",
        "group_ids",
        "active",
    ],
    "mail.template": [
        "name",
        "description",
        "model_id",
        "subject",
        "email_from",
        "email_to",
        "partner_to",
        "use_default_to",
        "lang",
        "report_template_ids",
        "auto_delete",
        "active",
        "body_html",
    ],
    "mail.message.subtype": [
        "name",
        "description",
        "res_model",
        "relation_field",
        "parent_id",
        "sequence",
        "default",
        "internal",
        "hidden",
        "track_recipients",
    ],
}


ATTRIB_ORDER: dict[str, list[str]] = {
    "record": [
        "id",
        "model",
    ],
    "field": [
        "name",
        "eval",
        "ref",
        "type",
        "file",
    ],
    "menuitem": [
        "id",
        "name",
        "parent",
        "action",
        "sequence",
        "groups",
        "web_icon",
        "web_keywords",
        "active",
    ],
    "template": [
        "id",
        "name",
        "inherit_id",
        "mode",
        "priority",
        "groups",
        "active",
    ],
    "delete": [
        "id",
        "model",
        "search",
    ],
    "function": [
        "model",
        "name",
        "eval",
        "context",
    ],
}

ARCH_ATTRIB_ORDER: list[str] = [
    "name",
    "for",
    "expr",
    "position",
    "id",
    "special",
    "type",
    "string",
    "title",
    "placeholder",
    "help",
    "confirm",
    "widget",
    "icon",
    "mode",
    "display",
    "orientation",
    "col",
    "colspan",
    "width",
    "nolabel",
    "optional",
    "password",
    "digits",
    "filename",
    "sum",
    "avg",
    "operator",
    "default_focus",
    "force_save",
    "domain",
    "filter_domain",
    "context",
    "options",
    "date",
    "default_period",
    "default_order",
    "default_group_by",
    "limit",
    "editable",
    "create",
    "edit",
    "delete",
    "duplicate",
    "import",
    "export_xlsx",
    "multi_edit",
    "sample",
    "open_form_view",
    "groups",
    "invisible",
    "column_invisible",
    "readonly",
    "required",
    "add",
    "remove",
    "separator",
    "class",
    "style",
]

ARCH_TAGS: frozenset[str] = frozenset(
    {
        "form",
        "list",
        "kanban",
        "search",
        "calendar",
        "graph",
        "pivot",
        "activity",
        "gantt",
        "cohort",
        "map",
        "hierarchy",
        "grid",
        "sheet",
        "header",
        "footer",
        "notebook",
        "page",
        "group",
        "separator",
        "label",
        "field",
        "button",
        "widget",
        "filter",
        "searchpanel",
        "chatter",
        "app",
        "block",
        "setting",
        "xpath",
        "attribute",
    }
)

_XML_DECL = b'<?xml version="1.0" encoding="utf-8"?>'

_PARSER = etree.XMLParser(remove_comments=False, strip_cdata=False)

_TOP_LEVEL_TAGS = frozenset(ATTRIB_ORDER) - {"record", "field"}


def expected_field_order(present_fields: list[str], model: str) -> list[str]:
    canonical = FIELD_ORDER.get(model)
    if canonical is None:
        return present_fields
    counts = Counter(present_fields)
    known = [name for name in canonical for _ in range(counts[name])]
    unknown = sorted(name for name in present_fields if name not in set(canonical))
    return known + unknown


def expected_attrib_order(tag: str, present_attribs: list[str]) -> list[str]:
    canonical = ATTRIB_ORDER.get(tag)
    if canonical is None:
        return present_attribs
    known = [k for k in canonical if k in present_attribs]
    unknown = sorted(k for k in present_attribs if k not in set(canonical))
    return known + unknown


def expected_arch_attrib_order(present_attribs: list[str]) -> list[str]:
    known = [k for k in ARCH_ATTRIB_ORDER if k in present_attribs]
    unknown = sorted(k for k in present_attribs if k not in set(ARCH_ATTRIB_ORDER))
    return known + unknown


def _reorder(element: etree._Element, canonical: list[str]) -> bool:
    attribs = dict(element.attrib)
    if list(attribs) == canonical:
        return False
    element.attrib.clear()
    for k in canonical:
        element.set(k, attribs[k])
    return True


def _normalize_attribs(element: etree._Element) -> bool:
    tag = element.tag
    if callable(tag):
        return False
    return _reorder(element, expected_attrib_order(tag, list(element.attrib)))


def is_model_view(record: etree._Element) -> bool:
    if record.get("model") != "ir.ui.view":
        return False
    model = record.find("field[@name='model']")
    return model is not None and bool((model.text or "").strip())


def iter_arch_elements(record: etree._Element):
    arch = record.find("field[@name='arch']")
    if arch is None:
        return
    for element in arch.iter(*ARCH_TAGS):
        if not callable(element.tag):
            yield element


def _normalize_arch(record: etree._Element) -> bool:
    modified = False
    for element in iter_arch_elements(record):
        if _reorder(element, expected_arch_attrib_order(list(element.attrib))):
            modified = True
    return modified


def _field_groups(
    record: etree._Element,
) -> tuple[list[list[etree._Element]], list[etree._Element]]:
    groups: list[list[etree._Element]] = []
    others: list[etree._Element] = []
    pending: list[etree._Element] = []
    for child in record:
        if callable(child.tag):
            pending.append(child)
        elif child.tag == "field":
            groups.append([*pending, child])
            pending = []
        else:
            others.extend(pending)
            others.append(child)
            pending = []
    others.extend(pending)
    return groups, others


def _sort_record_fields(record: etree._Element, model: str) -> bool:
    groups, others = _field_groups(record)
    if len(groups) <= 1:
        return False

    actual_names = [group[-1].get("name") for group in groups]
    expected_names = expected_field_order(actual_names, model)
    if actual_names == expected_names:
        return False

    original_tails = [group[-1].tail for group in groups]

    queues: dict[str | None, list[list[etree._Element]]] = {}
    for group in groups:
        queues.setdefault(group[-1].get("name"), []).append(group)
    ordered = [queues[name].pop(0) for name in expected_names]

    for child in list(record):
        record.remove(child)
    for index, group in enumerate(ordered):
        field = group[-1]
        positional_tail = original_tails[index]
        own_is_whitespace = field.tail is None or not field.tail.strip()
        positional_is_whitespace = (
            positional_tail is None or not positional_tail.strip()
        )
        if own_is_whitespace and positional_is_whitespace:
            field.tail = positional_tail
        for element in group:
            record.append(element)
    for element in others:
        record.append(element)

    return True


def sort_xml_file(
    path: Path,
    *,
    models: set[str] | None = None,
    dry_run: bool = False,
) -> bool | None:
    source = path.read_bytes()
    try:
        tree = etree.parse(BytesIO(source), _PARSER)
    except etree.XMLSyntaxError as exc:
        print(f"  SKIP  {path}: {exc}", file=sys.stderr)
        return None

    root = tree.getroot()
    was_modified = False

    for record in root.iter("record"):
        model = record.get("model")
        if model is None:
            continue
        if models is not None and model not in models:
            continue

        if _normalize_attribs(record):
            was_modified = True

        for field in record:
            if not callable(field.tag) and field.tag == "field":
                if _normalize_attribs(field):
                    was_modified = True

        if model in FIELD_ORDER and _sort_record_fields(record, model):
            was_modified = True

        if is_model_view(record) and _normalize_arch(record):
            was_modified = True

    for tag in _TOP_LEVEL_TAGS:
        for elem in root.iter(tag):
            if _normalize_attribs(elem):
                was_modified = True

    if not was_modified:
        return False

    buf = BytesIO()
    tree.write(buf, xml_declaration=False, encoding="utf-8", pretty_print=False)
    body = buf.getvalue()

    had_decl = source.lstrip().startswith(b"<?xml")
    new_content = (_XML_DECL + b"\n" + body) if had_decl else body

    if source.endswith(b"\n") and not new_content.endswith(b"\n"):
        new_content += b"\n"

    if not preserves_content(source, new_content):
        print(
            f"  SKIP  {path}: the sorted output would not say the same thing",
            file=sys.stderr,
        )
        return None

    if not dry_run:
        path.write_bytes(new_content)

    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Sort Odoo XML <record> <field> children and normalize element "
            "attribute order."
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
        "--model",
        metavar="MODEL",
        action="append",
        dest="models",
        help=(
            "Only process records of this model (repeatable); default: all known models"
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

    model_filter: set[str] | None = set(args.models) if args.models else None
    excluded: set[str] = set(args.exclude)
    changed = unchanged = skipped = 0

    for xml_file in _pretty_xml.iter_target_files(args.roots, excluded):
        result = sort_xml_file(xml_file, models=model_filter, dry_run=args.dry_run)
        if result is None:
            skipped += 1
        elif result:
            label = "would sort" if args.dry_run else "sorted   "
            print(f"  {label}  {xml_file}")
            changed += 1
        else:
            unchanged += 1

    verb = "would change" if args.dry_run else "sorted"
    print(f"\nDone: {changed} {verb}, {unchanged} unchanged, {skipped} skipped")


if __name__ == "__main__":
    main()
