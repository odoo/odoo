from unittest.mock import patch

import psycopg

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install", "partner_scoring")
class TestResPartnerAttributeLine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Attribute = cls.env["res.partner.attribute"]
        cls.Value = cls.env["res.partner.attribute.value"]
        cls.Line = cls.env["res.partner.attribute.line"]
        cls.Partner = cls.env["res.partner"]

        cls.company = cls.Partner.create(
            {"name": "Test EAV Company", "is_company": True}
        )
        cls.child = cls.Partner.create(
            {"name": "Test EAV Child", "parent_id": cls.company.id}
        )

        cls.attr_single = cls.Attribute.create(
            {"name": "Line Single Attribute", "value_type": "single"}
        )
        cls.val_a = cls.Value.create(
            {"name": "Value A", "attribute_id": cls.attr_single.id}
        )
        cls.val_b = cls.Value.create(
            {"name": "Value B", "attribute_id": cls.attr_single.id}
        )
        cls.attr_multi = cls.Attribute.create(
            {"name": "Line Multi Attribute", "value_type": "multi"}
        )
        cls.val_m1 = cls.Value.create(
            {"name": "Multi 1", "attribute_id": cls.attr_multi.id}
        )
        cls.val_m2 = cls.Value.create(
            {"name": "Multi 2", "attribute_id": cls.attr_multi.id}
        )

    def test_line_on_commercial_partner_ok(self):
        line = self.Line.create(
            {
                "partner_id": self.company.id,
                "attribute_id": self.attr_single.id,
                "value_ids": [(6, 0, self.val_a.ids)],
            }
        )
        self.assertEqual(line.value_ids, self.val_a)
        self.assertIn(line, self.company.attribute_line_ids)

    def test_line_on_child_rejected(self):
        with self.assertRaises(ValidationError):
            self.Line.create(
                {"partner_id": self.child.id, "attribute_id": self.attr_single.id}
            )

    def test_foreign_value_rejected(self):
        with self.assertRaises(ValidationError):
            self.Line.create(
                {
                    "partner_id": self.company.id,
                    "attribute_id": self.attr_single.id,
                    "value_ids": [(6, 0, self.val_m1.ids)],
                }
            )

    def test_single_rejects_multiple_values(self):
        with self.assertRaises(ValidationError):
            self.Line.create(
                {
                    "partner_id": self.company.id,
                    "attribute_id": self.attr_single.id,
                    "value_ids": [(6, 0, (self.val_a + self.val_b).ids)],
                }
            )

    def test_multi_allows_multiple_values(self):
        line = self.Line.create(
            {
                "partner_id": self.company.id,
                "attribute_id": self.attr_multi.id,
                "value_ids": [(6, 0, (self.val_m1 + self.val_m2).ids)],
            }
        )
        self.assertEqual(line.value_ids, self.val_m1 + self.val_m2)

    def test_unique_attribute_per_partner(self):
        self.Line.create(
            {"partner_id": self.company.id, "attribute_id": self.attr_single.id}
        )
        with (
            self.assertRaises(psycopg.IntegrityError),
            mute_logger("odoo.db.cursor"),
            self.cr.savepoint(),
        ):
            self.Line.create(
                {"partner_id": self.company.id, "attribute_id": self.attr_single.id}
            )
            self.env.flush_all()

    def test_a_sequence_write_does_not_rescore(self):
        """A handle drag is not a capture; the score rows do not move."""
        line = self.Line.create(
            {
                "partner_id": self.company.id,
                "attribute_id": self.attr_single.id,
                "value_ids": [(6, 0, self.val_a.ids)],
            }
        )
        with patch.object(type(self.Partner), "_score_refresh") as rescored:
            line.sequence = 7
            self.assertFalse(rescored.called)
            line.value_ids = [(6, 0, self.val_b.ids)]
            self.assertTrue(rescored.called)

    def test_demoting_a_company_moves_its_captured_attributes_up(self):
        """The constraint cannot see a change on the partner, so write() does."""
        demoted = self.Partner.create({"name": "Line Demoted", "is_company": True})
        line = self.Line.create(
            {
                "partner_id": demoted.id,
                "attribute_id": self.attr_single.id,
                "value_ids": [(6, 0, self.val_a.ids)],
            }
        )
        parent = self.Partner.create(
            {"name": "Line New Commercial", "is_company": True}
        )

        demoted.write({"parent_id": parent.id, "is_company": False})

        self.assertEqual(demoted.commercial_partner_id, parent)
        self.assertEqual(line.partner_id, parent)
        line._check_commercial_partner()

    def test_an_archived_line_follows_the_demoted_company_too(self):
        demoted = self.Partner.create(
            {"name": "Line Demoted Archived", "is_company": True}
        )
        line = self.Line.create(
            {
                "partner_id": demoted.id,
                "attribute_id": self.attr_single.id,
                "value_ids": [(6, 0, self.val_a.ids)],
            }
        )
        line.active = False
        parent = self.Partner.create(
            {"name": "Line Parent Archived", "is_company": True}
        )

        demoted.write({"parent_id": parent.id, "is_company": False})

        self.assertEqual(line.partner_id, parent)

    @mute_logger("odoo.addons.partner_scoring.models.res_partner")
    def test_a_captured_attribute_the_new_parent_already_answers_stays_put(self):
        demoted = self.Partner.create(
            {"name": "Line Demoted Conflict", "is_company": True}
        )
        parent = self.Partner.create(
            {"name": "Line Parent Conflict", "is_company": True}
        )
        stray = self.Line.create(
            {
                "partner_id": demoted.id,
                "attribute_id": self.attr_single.id,
                "value_ids": [(6, 0, self.val_a.ids)],
            }
        )
        held = self.Line.create(
            {
                "partner_id": parent.id,
                "attribute_id": self.attr_single.id,
                "value_ids": [(6, 0, self.val_b.ids)],
            }
        )

        demoted.write({"parent_id": parent.id, "is_company": False})

        # Two captures of one attribute cannot be merged without deciding
        # which answer wins, so nothing is silently destroyed.
        self.assertEqual(stray.partner_id, demoted)
        self.assertEqual(held.partner_id, parent)
        self.assertEqual(held.value_ids, self.val_b)
