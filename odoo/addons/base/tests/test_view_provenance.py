from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestViewProvenance(TransactionCase):
    """`get_provenance` says which view put each node of a combined arch
    where it is — the primary for its own nodes, the overlay that inserted
    the others; an overlay that only edits attributes owns no node."""

    def setUp(self):
        super().setUp()
        View = self.env["ir.ui.view"]
        self.primary = View.create(
            {
                "name": "provenance primary",
                "model": "res.partner",
                "arch": """
                    <form>
                        <sheet>
                            <group name="main"><field name="name"/></group>
                        </sheet>
                    </form>
                """,
            }
        )
        self.adder = View.create(
            {
                "name": "provenance adder",
                "model": "res.partner",
                "inherit_id": self.primary.id,
                "arch": """
                    <group name="main" position="inside">
                        <field name="email"/>
                        <group name="extra"><field name="website"/></group>
                    </group>
                """,
            }
        )
        self.editor = View.create(
            {
                "name": "provenance editor",
                "model": "res.partner",
                "inherit_id": self.primary.id,
                "arch": """
                    <field name="name" position="attributes">
                        <attribute name="readonly">1</attribute>
                    </field>
                """,
            }
        )

    def test_nodes_are_owned_by_the_view_that_put_them_there(self):
        provenance = self.primary.get_provenance()
        by_view = {
            self.primary.id: {"form", "sheet", "group:main", "field:name"},
            self.adder.id: {"field:email", "group:extra", "field:website"},
        }
        for view_id, node_ids in by_view.items():
            for node_id in node_ids:
                self.assertEqual(provenance[node_id]["view_id"], view_id, node_id)
        self.assertEqual(provenance["field:website"]["kind"], "field")
        self.assertNotIn(self.editor.id, {p["view_id"] for p in provenance.values()})
        # the edit itself landed
        self.assertIn(
            'readonly="1"',
            self.primary.with_context(
                check_view_ids=(self.editor + self.adder).ids
            ).get_view(self.primary.id)["arch"],
        )

    def test_an_inheriting_view_reports_its_primary_tree(self):
        from_child = self.adder.get_provenance()
        self.assertEqual(from_child["field:email"]["view_id"], self.adder.id)
        self.assertEqual(from_child["form"]["view_id"], self.primary.id)
        self.assertIsNone(from_child["form"]["xml_id"])

    def test_branding_yields_nothing(self):
        self.assertEqual(
            self.primary.with_context(inherit_branding=True).get_provenance(), {}
        )

    def test_provenance_survives_a_spec_the_ids_cannot_name(self):
        # `$0` in running text is the XML combine's to apply; the nodes the
        # earlier overlay put in are still its afterwards
        View = self.env["ir.ui.view"]
        wrapper = View.create(
            {
                "name": "provenance wrapper",
                "model": "res.partner",
                "inherit_id": self.primary.id,
                "priority": 99,
                "arch": """
                    <field name="website" position="replace">
                        <div>see $0 here</div>
                    </field>
                """,
            }
        )
        provenance = self.primary.get_provenance()
        self.assertEqual(provenance["field:email"]["view_id"], self.adder.id)
        self.assertEqual(provenance["div"]["view_id"], wrapper.id)
        self.assertEqual(provenance["form"]["view_id"], self.primary.id)

    def test_a_later_overlay_still_addresses_the_tree_by_id(self):
        View = self.env["ir.ui.view"]
        View.create(
            {
                "name": "provenance wrapper",
                "model": "res.partner",
                "inherit_id": self.primary.id,
                "priority": 98,
                "arch": """
                    <field name="website" position="replace">
                        <div>see $0 here</div>
                    </field>
                """,
            }
        )
        later = View.create(
            {
                "name": "provenance later",
                "model": "res.partner",
                "inherit_id": self.primary.id,
                "priority": 99,
                "arch": """
                    <div position="inside"><field name="function"/></div>
                """,
            }
        )
        provenance = self.primary.get_provenance()
        self.assertEqual(provenance["field:function"]["view_id"], later.id)
