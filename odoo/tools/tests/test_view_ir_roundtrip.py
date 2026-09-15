import unittest
from pathlib import Path

from lxml import etree

from odoo.tools import view_ir

REPO_ROOT = Path(__file__).resolve().parents[3]
ADDON_ROOTS = (REPO_ROOT / "addons", REPO_ROOT / "odoo" / "addons")
SKIP_PARTS = frozenset({"static", "node_modules", "__pycache__", "i18n", "lib"})
PARSER = etree.XMLParser(huge_tree=True)


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

    def test_a_comment_is_a_node_and_the_text_around_it_stays_put(self):
        node = view_ir.from_string(
            "<form> a <!-- c --> b <field name='x'/> d <!-- e --> f </form>"
        )
        self.assertEqual(node.text, " a ")
        self.assertEqual(
            [(child.kind, child.text, child.tail) for child in node.children],
            [
                (view_ir.COMMENT, " c ", " b "),
                ("field", None, " d "),
                (view_ir.COMMENT, " e ", " f "),
            ],
        )
        self.assertEqual(
            view_ir.to_string(node),
            '<form> a <!-- c --> b <field name="x"/> d <!-- e --> f </form>',
        )

    def test_json_form_omits_empty_members(self):
        node = view_ir.from_string("<list><field name='x'/></list>")
        self.assertEqual(
            node.to_dict(),
            {"kind": "list", "children": [{"kind": "field", "attrs": {"name": "x"}}]},
        )
        self.assertEqual(view_ir.Node.from_dict(node.to_dict()), node)


class TestViewIrMarkup(unittest.TestCase):
    ARCH = (
        "<form><!-- lead -->"
        '<?odoo hint="x"?>'
        '<group><!--[if mso]>outlook<![endif]--><field name="a"/><!-- after --></group>'
        "</form>"
    )

    def test_comments_and_processing_instructions_survive_the_round_trip(self):
        element = etree.fromstring(self.ARCH)
        node = view_ir.from_arch(element)
        self.assertEqual(
            [child.kind for child in node.children],
            [view_ir.COMMENT, view_ir.PROCESSING_INSTRUCTION, "group"],
        )
        self.assertEqual(node.children[0].text, " lead ")
        self.assertEqual(node.children[1].attrs, {"target": "odoo"})
        self.assertEqual(node.children[1].text, 'hint="x"')
        group = node.children[2]
        self.assertEqual(
            [child.kind for child in group.children],
            [view_ir.COMMENT, "field", view_ir.COMMENT],
        )
        self.assertEqual(group.children[0].text, "[if mso]>outlook<![endif]")
        self.assertEqual(
            etree.tostring(view_ir.to_arch(node), encoding="unicode"), self.ARCH
        )
        self.assertEqual(view_ir.from_json(view_ir.to_json(node)), node)

    def test_markup_cannot_be_a_root(self):
        with self.assertRaises(ValueError):
            view_ir.to_arch(view_ir.Node(view_ir.COMMENT, text="alone"))

    def test_the_validator_passes_over_markup(self):
        node = view_ir.from_arch(etree.fromstring(self.ARCH))
        self.assertEqual(
            [issue.code for issue in view_ir.get_issues(node, "form")],
            [],
        )
