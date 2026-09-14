import re
import unittest
from pathlib import Path

from lxml import etree

from odoo.tools import view_ir
from odoo.tools.view_ir.validate import _check_value

REPO_ROOT = Path(__file__).resolve().parents[3]
ADDON_ROOTS = (REPO_ROOT / "addons", REPO_ROOT / "odoo" / "addons")
SKIP_PARTS = frozenset({"static", "node_modules", "__pycache__", "i18n", "lib"})
PARSER = etree.XMLParser(remove_comments=True, huge_tree=True)
LAST_STEP = re.compile(r"([A-Za-z_][\w-]*)(?:\[[^\]]*\])*\s*$")


def iter_view_records():
    for root in ADDON_ROOTS:
        for path in root.rglob("*.xml"):
            parts = path.relative_to(root).parts
            if SKIP_PARTS & set(parts):
                continue
            try:
                tree = etree.parse(str(path), PARSER)
            except etree.XMLSyntaxError:
                continue
            for record in tree.iter("record"):
                if record.get("model") != "ir.ui.view" or not record.get("id"):
                    continue
                fields = {
                    field.get("name"): field for field in record.iterchildren("field")
                }
                if (fields.get("type") is not None) and (
                    (fields["type"].text or "").strip() == "qweb"
                ):
                    continue
                arch = fields.get("arch")
                body = (
                    [el for el in arch if isinstance(el.tag, str)]
                    if arch is not None
                    else []
                )
                if not body:
                    continue
                inherit = fields.get("inherit_id")
                yield (
                    path,
                    _qualify(parts[0], record.get("id")),
                    body[0],
                    _qualify(parts[0], inherit.get("ref"))
                    if inherit is not None
                    else None,
                )


def _qualify(module, xmlid):
    if not xmlid:
        return None
    return xmlid if "." in xmlid else f"{module}.{xmlid}"


class TestViewIrCorpus(unittest.TestCase):
    """Every view the checkout ships reads as valid to the schema that installing it
    enforces, inherited fragments included, so a gap in the schema reads here
    instead of as a ParseError halfway through an install."""

    def test_every_view_in_the_checkout_validates(self):
        spec = view_ir.schema()
        records = {
            xmlid: (path, top, parent)
            for path, xmlid, top, parent in iter_view_records()
        }

        def view_type_of(xmlid, seen=()):
            if xmlid not in records or xmlid in seen:
                return None
            _path, top, parent = records[xmlid]
            return spec.view_type_of(top.tag) or (
                parent and view_type_of(parent, (*seen, xmlid))
            )

        errors = []
        for xmlid, (path, top, _parent) in records.items():
            view_type = view_type_of(xmlid)
            if view_type is None:
                continue
            where = f"{path.relative_to(REPO_ROOT)}#{xmlid}"
            if spec.view_type_of(top.tag):
                fragments = [top]
            else:
                fragments = []
                patches = (
                    [top]
                    if top.get("position") or top.tag == "xpath"
                    else [el for el in top if isinstance(el.tag, str)]
                )
                for patch in patches:
                    if patch.get("position") == "attributes":
                        errors.extend(
                            f"{where}: {problem}"
                            for problem in _attribute_problems(spec, view_type, patch)
                        )
                    else:
                        fragments.extend(
                            el
                            for el in patch
                            if isinstance(el.tag, str) and el.tag != "attribute"
                        )
            for fragment in fragments:
                errors.extend(
                    f"{where}: {issue}"
                    for issue in view_ir.validate(
                        view_ir.from_arch(fragment), view_type
                    )
                    if issue.severity == "error"
                    and not (
                        fragment is not top
                        and issue.code == "missing-attr"
                        and not issue.path
                    )
                )
        self.assertGreater(
            len(records), 3000, "the walk matched too little to mean anything"
        )
        self.assertEqual(errors, [])


def _attribute_problems(spec, view_type, patch):
    if patch.tag == "xpath":
        step = LAST_STEP.search(patch.get("expr", ""))
        target = step.group(1) if step else None
    else:
        target = patch.tag
    if not target or spec.node_spec(view_type, target) is None:
        return
    for attribute in patch.iterchildren("attribute"):
        value = (attribute.text or "").strip()
        if attribute.get("add") or attribute.get("remove") or not value:
            continue
        attr_type = spec.attr_type(view_type, target, attribute.get("name"))
        if attr_type is not None and (problem := _check_value(attr_type, value)):
            yield f"bad-{problem} at {target}: {attribute.get('name')}={value!r}"
