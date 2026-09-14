import unittest
from pathlib import Path

from lxml import etree

from odoo.tools import view_ir

REPO_ROOT = Path(__file__).resolve().parents[3]
ADDON_ROOTS = (REPO_ROOT / "addons", REPO_ROOT / "odoo" / "addons")
SKIP_PARTS = frozenset({"static", "node_modules", "__pycache__", "i18n", "lib"})
PARSER = etree.XMLParser(remove_comments=True, huge_tree=True)


def iter_archs():
    for root in ADDON_ROOTS:
        for path in root.rglob("*.xml"):
            if SKIP_PARTS & set(path.relative_to(root).parts):
                continue
            try:
                tree = etree.parse(str(path), PARSER)
            except etree.XMLSyntaxError:
                continue
            for record in tree.iter("record"):
                if record.get("model") != "ir.ui.view":
                    continue
                for field in record.iterchildren("field"):
                    if field.get("name") == "arch":
                        for element in field:
                            if isinstance(element.tag, str):
                                yield path, record.get("id"), element


class TestViewIrRoundTrip(unittest.TestCase):
    def test_every_arch_in_the_checkout_survives_the_round_trip(self):
        count = 0
        diffs = []
        for path, xmlid, element in iter_archs():
            count += 1
            node = view_ir.from_arch(element)
            rebuilt = view_ir.to_arch(node)
            if view_ir.canonical(element) != view_ir.canonical(rebuilt):
                diffs.append(f"{path.relative_to(REPO_ROOT)}#{xmlid}")
            elif view_ir.from_json(view_ir.to_json(node)) != node:
                diffs.append(f"{path.relative_to(REPO_ROOT)}#{xmlid} (json)")
        self.assertGreater(count, 3000, "the walk matched too little to mean anything")
        self.assertEqual(diffs, [])

    def test_namespaced_subtree_keeps_its_prefix(self):
        arch = (
            '<kanban><templates><t t-name="card">'
            '<svg xmlns:svg="http://www.w3.org/2000/svg"><svg:circle r="1"/></svg>'
            "</t></templates></kanban>"
        )
        element = etree.fromstring(arch)
        node = view_ir.from_arch(element)
        self.assertEqual(
            view_ir.canonical(view_ir.to_arch(node)), view_ir.canonical(element)
        )
        self.assertEqual(
            node.children[0].children[0].children[0].nsmap,
            {"svg": "http://www.w3.org/2000/svg"},
        )

    def test_text_and_tail_are_preserved(self):
        node = view_ir.from_string(
            "<form> a <field name='x'/> b <span>c</span>d</form>"
        )
        self.assertEqual(node.text, " a ")
        self.assertEqual(node.children[0].tail, " b ")
        self.assertEqual(node.children[1].text, "c")
        self.assertEqual(node.children[1].tail, "d")
        self.assertEqual(
            view_ir.to_string(node),
            '<form> a <field name="x"/> b <span>c</span>d</form>',
        )

    def test_text_after_a_comment_is_kept(self):
        node = view_ir.from_string(
            "<form> a <!-- c --> b <field name='x'/> d <!-- e --> f </form>"
        )
        self.assertEqual(node.text, " a  b ")
        self.assertEqual(node.children[0].tail, " d  f ")
        self.assertEqual(
            view_ir.to_string(node), '<form> a  b <field name="x"/> d  f </form>'
        )

    def test_json_form_omits_empty_members(self):
        node = view_ir.from_string("<list><field name='x'/></list>")
        self.assertEqual(
            node.to_dict(),
            {"kind": "list", "children": [{"kind": "field", "attrs": {"name": "x"}}]},
        )
        self.assertEqual(view_ir.Node.from_dict(node.to_dict()), node)
