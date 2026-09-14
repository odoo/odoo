from collections import defaultdict

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCopyDataContract(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]

    def test_duplicated_recordset_is_refused_by_copy_data(self):
        partner = self.Partner.create({"name": "Copy Contract"})
        twice = self.Partner.browse([partner.id, partner.id])
        self.assertEqual(len(twice), 2)

        with self.assertRaises(ValueError) as capture:
            twice.copy_data()
        self.assertIn("more than once", str(capture.exception))

        with self.assertRaises(ValueError):
            twice.copy()

    def test_deduplicated_recordset_copies_normally(self):
        partner = self.Partner.create({"name": "Copy Contract Dedup"})
        copies = self.Partner.browse([partner.id]).copy()
        self.assertEqual(len(copies), 1)
        self.assertNotEqual(copies, partner)

    def test_distinct_records_stay_paired_with_their_copies(self):
        partners = self.Partner.create(
            [{"name": "Copy Pair A"}, {"name": "Copy Pair B"}]
        )
        vals_list = partners.copy_data()
        self.assertEqual(len(vals_list), len(partners))
        self.assertTrue(all(vals is not None for vals in vals_list))
        for partner, vals in zip(partners, vals_list, strict=True):
            self.assertIn(partner.name, vals["name"])

    def _make_group(self, name):
        return self.env["res.groups"].create(
            {
                "name": name,
                "model_access": [
                    (
                        0,
                        0,
                        {
                            "name": name,
                            "model_id": self.env["ir.model"]._get_id("res.partner"),
                        },
                    )
                ],
            }
        )

    def test_already_copied_o2m_lines_never_reach_the_child_copy_data(self):
        group = self._make_group("Copy Group")
        line = group.model_access
        self.assertTrue(line, "the fixture needs a copied one2many line")

        seen = defaultdict(set)
        seen["ir.model.access"].add(line.id)

        received = []
        line_cls = type(self.env["ir.model.access"])
        original = line_cls.copy_data

        def spy(records, default=None):
            received.append(tuple(records.ids))
            return original(records, default)

        self.patch(line_cls, "copy_data", spy)
        vals_list = group.with_context(__copy_data_seen=seen).copy_data()

        self.assertNotIn(
            (line.id,),
            received,
            "an already-copied line must not be passed to the child copy_data",
        )
        self.assertEqual(vals_list[0].get("model_access", []), [])
        self.assertTrue(all(vals is not None for vals in vals_list))

    def test_normal_o2m_lines_are_still_copied(self):
        group = self._make_group("Copy Group Kept")
        copy = group.copy()
        self.assertEqual(len(copy.model_access), 1)
        self.assertEqual(copy.model_access.name, "Copy Group Kept")
        self.assertNotEqual(copy.model_access, group.model_access)
