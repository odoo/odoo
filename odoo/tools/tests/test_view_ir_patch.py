import unittest

from odoo.tools import view_ir
from odoo.tools.view_ir import Node
from odoo.tools.view_ir.patch import AttrChange, Move, Patch, PatchError, apply

BASE = """
<form>
    <header><button name="confirm" type="object"/></header>
    <sheet>
        <group name="main">
            <field name="partner_id"/>
            <field name="date" invisible="state == 'done'" class="a b"/>
        </group>
        <notebook><page name="lines"><field name="line_ids"/></page></notebook>
    </sheet>
</form>
"""


def base():
    return view_ir.from_string(BASE)


def node(arch):
    return view_ir.from_string(arch)


def kinds(parent):
    return [f"{c.kind}:{c.attrs.get('name', '')}" for c in parent.children]


class TestPatchAlgebra(unittest.TestCase):
    def test_before_after_inside_place_content_around_the_target(self):
        applied = apply(
            base(),
            [
                Patch(
                    "before",
                    "field:partner_id",
                    (node("<field name='ref'/>"),),
                    origin="a",
                ),
                Patch(
                    "after",
                    "field:date",
                    (node("<field name='user_id'/>"),),
                    origin="a",
                ),
                Patch(
                    "inside", "group:main", (node("<field name='note'/>"),), origin="a"
                ),
            ],
        )
        ids = view_ir.identify(applied.root)
        self.assertEqual(
            kinds(ids["group:main"]),
            [
                "field:ref",
                "field:partner_id",
                "field:date",
                "field:user_id",
                "field:note",
            ],
        )
        self.assertEqual(ids["field:ref"].origin, "a")
        self.assertIsNone(ids["field:partner_id"].origin)

    def test_replace_swaps_the_node_and_stamps_the_content(self):
        applied = apply(
            base(),
            [
                Patch(
                    "replace",
                    "field:partner_id",
                    (node("<div class='wrap'><field name='company_id'/></div>"),),
                    origin="b",
                )
            ],
        )
        ids = view_ir.identify(applied.root)
        self.assertNotIn("field:partner_id", ids)
        wrap = ids["group:main"].children[0]
        self.assertEqual(wrap.attrs["class"], "wrap")
        self.assertEqual(kinds(wrap), ["field:company_id"])
        self.assertEqual(ids["field:company_id"].origin, "b")

    def test_dollar_zero_anywhere_in_the_content_is_the_replaced_node(self):
        applied = apply(
            base(),
            [
                Patch(
                    "replace",
                    "field:partner_id",
                    (
                        Node(
                            "div", {"class": "w"}, [Node("span", children=[Node("$0")])]
                        ),
                    ),
                    origin="b",
                )
            ],
        )
        ids = view_ir.identify(applied.root)
        wrap = ids["group:main"].children[0]
        self.assertEqual(wrap.children[0].children[0].attrs, {"name": "partner_id"})
        self.assertIs(wrap.children[0].children[0], ids["field:partner_id"])
        self.assertIsNone(ids["field:partner_id"].origin)
        self.assertEqual(wrap.origin, "b")
        with self.assertRaises(PatchError):
            apply(base(), [Patch("inside", "sheet", (Node("$0"),))])

    def test_replace_inner_keeps_the_node_and_swaps_its_children(self):
        applied = apply(
            base(),
            [Patch("replace_inner", "group:main", (node("<field name='only'/>"),))],
        )
        ids = view_ir.identify(applied.root)
        self.assertEqual(ids["group:main"].attrs["name"], "main")
        self.assertEqual(kinds(ids["group:main"]), ["field:only"])

    def test_remove_drops_the_node(self):
        applied = apply(base(), [Patch("remove", "field:date")])
        self.assertEqual(
            kinds(view_ir.identify(applied.root)["group:main"]), ["field:partner_id"]
        )

    def test_move_takes_a_base_node_to_the_content_position(self):
        applied = apply(
            base(),
            [Patch("inside", "header", (Move("field:date"),), origin="mover")],
        )
        ids = view_ir.identify(applied.root)
        self.assertEqual(kinds(ids["header"]), ["button:confirm", "field:date"])
        self.assertEqual(kinds(ids["group:main"]), ["field:partner_id"])
        # a moved node keeps its provenance: the base still put it there
        self.assertIsNone(ids["field:date"].origin)

    def test_attributes_set_add_remove_and_unset(self):
        applied = apply(
            base(),
            [
                Patch(
                    "attributes",
                    "field:date",
                    attributes=(
                        AttrChange("invisible", add="not partner_id", separator="or"),
                        AttrChange("class", add="c", remove="a", separator=" "),
                        AttrChange("string", value="Date!"),
                        AttrChange("widget", value=""),
                    ),
                    origin="a",
                )
            ],
        )
        date = view_ir.identify(applied.root)["field:date"]
        self.assertEqual(
            date.attrs["invisible"], "(state == 'done') or (not partner_id)"
        )
        self.assertEqual(date.attrs["class"], "b c")
        self.assertEqual(date.attrs["string"], "Date!")
        self.assertNotIn("widget", date.attrs)
        self.assertEqual(applied.managed[("field:date", "string")], "a")
        self.assertEqual(applied.conflicts, [])

    def test_two_origins_setting_one_attribute_is_a_reported_conflict(self):
        applied = apply(
            base(),
            [
                Patch(
                    "attributes",
                    "field:date",
                    attributes=(AttrChange("string", "A"),),
                    origin="a",
                ),
                Patch(
                    "attributes",
                    "field:date",
                    attributes=(AttrChange("string", "B"),),
                    origin="b",
                ),
                Patch(
                    "attributes",
                    "field:date",
                    attributes=(AttrChange("string", "C"),),
                    origin="b",
                ),
            ],
        )
        self.assertEqual(
            view_ir.identify(applied.root)["field:date"].attrs["string"], "C"
        )
        self.assertEqual(len(applied.conflicts), 1)
        self.assertEqual(applied.conflicts[0].origins, ("a", "b"))
        self.assertEqual(applied.managed[("field:date", "string")], "b")

    def test_a_patch_addresses_what_the_previous_one_inserted(self):
        applied = apply(
            base(),
            [
                Patch("inside", "sheet", (node("<group name='extra'/>"),), origin="a"),
                Patch(
                    "inside", "group:extra", (node("<field name='x'/>"),), origin="b"
                ),
            ],
        )
        ids = view_ir.identify(applied.root)
        self.assertEqual(kinds(ids["group:extra"]), ["field:x"])
        self.assertEqual(ids["group:extra"].origin, "a")
        self.assertEqual(ids["field:x"].origin, "b")

    def test_the_root_can_only_be_replaced_whole(self):
        applied = apply(
            base(), [Patch("replace", "form", (node("<form string='New'/>"),))]
        )
        self.assertEqual(applied.root.attrs, {"string": "New"})
        with self.assertRaises(PatchError):
            apply(base(), [Patch("remove", "form")])
        with self.assertRaises(PatchError):
            apply(base(), [Patch("after", "form", (node("<div/>"),))])

    def test_an_unknown_target_is_refused_with_the_patch_named(self):
        with self.assertRaisesRegex(PatchError, "from 'mod': no node 'field:nope'"):
            apply(base(), [Patch("remove", "field:nope", origin="mod")])
        with self.assertRaises(PatchError):
            apply(base(), [Patch("inside", "sheet", (Move("field:nope"),))])

    def test_the_result_still_round_trips_as_arch(self):
        applied = apply(
            base(), [Patch("after", "field:date", (node("<field name='z'/>"),))]
        )
        self.assertIn('<field name="z"/>', view_ir.to_string(applied.root))
