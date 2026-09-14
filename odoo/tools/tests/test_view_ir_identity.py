import unittest

from odoo.tools import view_ir
from odoo.tools.view_ir import identify

FORM = """
<form string="Order">
    <header>
        <button name="action_confirm" type="object" string="Confirm"/>
        <field name="state" widget="statusbar"/>
    </header>
    <sheet>
        <group>
            <group><field name="partner_id"/><field name="date_order"/></group>
            <group><field name="user_id"/></group>
        </group>
        <notebook>
            <page name="lines" string="Lines">
                <field name="order_line"><list><field name="product_id"/></list></field>
            </page>
            <page string="Other"><field name="note"/></page>
        </notebook>
    </sheet>
    <chatter/>
</form>
"""


def ids_of(arch):
    root = view_ir.from_string(arch)
    return root, identify(root)


class TestIdentify(unittest.TestCase):
    def test_named_nodes_are_kind_colon_name(self):
        _root, ids = ids_of(FORM)
        for expected in (
            "button:action_confirm",
            "field:state",
            "field:partner_id",
            "field:order_line",
            "page:lines",
            "field:product_id",
        ):
            self.assertIn(expected, ids)
        self.assertEqual(ids["page:lines"].attrs["string"], "Lines")

    def test_a_kind_that_occurs_once_is_its_own_id(self):
        _root, ids = ids_of(FORM)
        for expected in ("form", "header", "sheet", "notebook", "chatter", "list"):
            self.assertEqual(ids[expected].kind, expected)

    def test_anonymous_nodes_hash_their_parent_and_own_kind_and_attributes(self):
        _root, ids = ids_of(FORM)
        anonymous = sorted(i for i in ids if i.startswith("group@"))
        self.assertEqual(len(anonymous), 3)
        outer = next(i for i in anonymous if ids[i].children[0].kind == "group")
        self.assertEqual(ids[outer].id, outer)
        # the two inner groups are alike (same parent, kind, no attributes):
        # document order tells them apart
        inner = sorted(i for i in anonymous if i != outer)
        self.assertEqual(inner[1], f"{inner[0]}#2")
        # the unnamed page is anonymous too, and distinct from the named one
        pages = [i for i in ids if i.startswith("page")]
        self.assertEqual(len(pages), 2)
        self.assertIn("page:lines", pages)

    def test_every_node_gets_a_unique_id(self):
        root, ids = ids_of(FORM)
        nodes = [node for _path, node in root.walk()]
        self.assertEqual(len(ids), len(nodes))
        self.assertTrue(all(node.id for node in nodes))
        self.assertEqual({node.id for node in nodes}, set(ids))

    def test_reordering_siblings_that_differ_keeps_every_id(self):
        root, ids = ids_of(FORM)
        before = {node.id: id(node) for node in ids.values()}
        ids["sheet"].children.reverse()
        ids["notebook"].children.reverse()
        identify(root)
        after = {node.id: id(node) for _path, node in root.walk()}
        self.assertEqual(before, after)

    def test_adding_a_child_keeps_an_anonymous_id(self):
        root, ids = ids_of(FORM)
        target = next(
            i
            for i in ids
            if i.startswith("group@")
            and ids[i].children[0].attrs.get("name") == "user_id"
        )
        ids[target].children.append(view_ir.from_string("<field name='team_id'/>"))
        self.assertIs(identify(root)[target], ids[target])

    def test_reparenting_changes_an_anonymous_id_and_keeps_a_named_one(self):
        root, ids = ids_of(FORM)
        inner_ids = sorted(i for i in ids if i.startswith("group@"))
        outer = next(i for i in inner_ids if ids[i].children[0].kind == "group")
        inner = next(
            i
            for i in inner_ids
            if i != outer and ids[i].children[0].attrs.get("name") == "partner_id"
        )
        moved = ids[inner]
        ids[outer].children.remove(moved)
        ids["sheet"].children.insert(0, moved)
        identify(root)
        self.assertNotEqual(moved.id, inner)
        self.assertTrue(moved.id.startswith("group@"))
        self.assertEqual(ids["field:partner_id"].id, "field:partner_id")

    def test_a_derived_id_used_twice_is_suffixed_in_document_order(self):
        root, ids = ids_of(
            "<list><header><field name='x'/></header><field name='x'/><field name='x'/></list>"
        )
        self.assertEqual(
            [node.id for node in root.find("field")],
            ["field:x", "field:x#2", "field:x#3"],
        )
        self.assertIs(ids["field:x#3"], list(root.find("field"))[2])

    def test_an_explicit_id_is_the_id_and_is_reserved(self):
        _root, ids = ids_of(
            "<form><div id='field:a'/><field name='a'/><group id='mine'><field name='b'/></group></form>"
        )
        self.assertEqual(ids["field:a"].kind, "div")
        self.assertEqual(ids["field:a#2"].kind, "field")
        self.assertEqual(ids["mine"].kind, "group")
        self.assertEqual(ids["field:b"].kind, "field")

    def test_an_explicit_id_an_arch_repeats_is_suffixed_like_a_derived_one(self):
        root = view_ir.from_string("<form><div id='x'/><div id='x'/></form>")
        identify(root)
        self.assertEqual([node.id for node in root.find("div")], ["x", "x#2"])

    def test_ids_are_not_part_of_the_wire_form(self):
        root, _ids = ids_of(FORM)
        self.assertNotIn('"id"', view_ir.to_json(root))
        self.assertEqual(view_ir.from_json(view_ir.to_json(root)), root)
