# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.product.tests.common import ProductCommon


class TestProductCatalog(ProductCommon):
    """Test the sections management through the product catalog."""

    _test_user_groups = ["account.group_account_user"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice = cls.env["account.move"].create({
            "partner_id": cls.partner.id,
            "line_ids": [
                Command.create({"name": "Section 1", "display_type": "line_section"}),
                Command.create({"name": "Subsection 1.1", "display_type": "line_subsection"}),
                Command.create({"name": "Subsection 1.2", "display_type": "line_subsection"}),
                Command.create({"name": "Subsection 1.3", "display_type": "line_subsection"}),
                Command.create({"name": "Section 2", "display_type": "line_section"}),
                Command.create({"name": "Section 3", "display_type": "line_section"}),
                Command.create({"name": "Subsection 3.1", "display_type": "line_subsection"}),
                Command.create({"name": "Subsection 3.2", "display_type": "line_subsection"}),
                Command.create({"name": "Subsection 3.3", "display_type": "line_subsection"}),
                Command.create({"name": "Section 4", "display_type": "line_section"}),
            ],
        })

        (
            cls.section1,
            cls.subsection11,
            cls.subsection12,
            cls.subsection13,
            cls.section2,
            cls.section3,
            cls.subsection31,
            cls.subsection32,
            cls.subsection33,
            cls.section4,
        ) = cls.invoice_lines = cls.invoice.line_ids

    def test_create_section(self):
        # New Section
        res = self.invoice.create_section(child_field="line_ids", name="New Section")

        self.assertEqual(res["id"], self.invoice["line_ids"][-1:].id)

        # New Subsection (Section with subsections)
        res = self.invoice.create_section(
            child_field="line_ids", name="New SubSection", parent_id=self.section1.id
        )
        self.assertEqual(res["id"], self.invoice["line_ids"].sorted("sequence")[4].id)

        # New Subsection (Section with subsections)
        res = self.invoice.create_section(
            child_field="line_ids", name="New SubSection", parent_id=self.section2.id
        )
        self.assertEqual(res["id"], self.invoice["line_ids"].sorted("sequence")[6].id)

    def test_delete_section(self):
        # Subsection
        self.invoice.delete_section("line_ids", self.subsection33.id)
        self.assertFalse(self.subsection33.exists())
        invoice_lines = self.invoice_lines - self.subsection33
        self.assertEqual(self.invoice["line_ids"], invoice_lines)

        # Section
        self.invoice.delete_section("line_ids", self.section2.id)
        self.assertFalse(self.section2.exists())
        invoice_lines = invoice_lines - self.section2
        self.assertEqual(self.invoice["line_ids"], invoice_lines)

        # Section with subsections
        self.invoice.delete_section("line_ids", self.section3.id)
        removed_lines = self.section3 | self.subsection31 | self.subsection32 | self.subsection33
        self.assertFalse(removed_lines.exists())
        invoice_lines = invoice_lines - removed_lines
        self.assertEqual(self.invoice["line_ids"], invoice_lines)

    def test_duplicate_section(self):
        # Last section
        res = self.invoice.duplicate_section("line_ids", self.section4.id)
        self.assertEqual(
            res["duplicated_section_id"], self.invoice["line_ids"].sorted("sequence")[-1:].id
        )

        # Section
        res = self.invoice.duplicate_section("line_ids", self.section2.id)
        self.assertEqual(
            res["duplicated_section_id"], self.invoice["line_ids"].sorted("sequence")[5].id
        )

        # Section with subsections
        res = self.invoice.duplicate_section("line_ids", self.section3.id)
        self.assertEqual(
            res["duplicated_section_id"], self.invoice["line_ids"].sorted("sequence")[10].id
        )
        self.assertEqual(len(self.invoice["line_ids"]), 16)

        # Subsection
        res = self.invoice.duplicate_section("line_ids", self.subsection33.id)
        self.assertEqual(
            res["duplicated_section_id"], self.invoice["line_ids"].sorted("sequence")[10].id
        )
        self.assertEqual(len(self.invoice["line_ids"]), 17)

    def test_rename_section(self):
        self.invoice.rename_section(
            child_field="line_ids", section_id=self.section1.id, new_name="First Section"
        )
        self.assertEqual(self.section1.name, "First Section")

    def test_resequence_sections(self):
        # Section after no section (at first place)
        self.invoice.resequence_sections("line_ids", self.section2.id)
        self.assertEqual(self.section2.id, self.invoice["line_ids"].sorted("sequence")[0].id)

        # Section after another section
        self.invoice.resequence_sections(
            "line_ids", self.section2.id, previous_section_id=self.section1.id
        )
        self.assertEqual(self.section2.id, self.invoice["line_ids"].sorted("sequence")[4].id)

        # Subsection after subsection (same parent)
        self.invoice.resequence_sections(
            "line_ids", self.subsection11.id, previous_section_id=self.subsection12.id
        )
        self.assertEqual(self.subsection11.id, self.invoice["line_ids"].sorted("sequence")[2].id)
        self.invoice.resequence_sections(
            "line_ids", self.subsection12.id, previous_section_id=self.subsection11.id
        )
        self.assertEqual(self.subsection12.id, self.invoice["line_ids"].sorted("sequence")[2].id)

        # Subsection into another section (first place | without subsection)
        self.invoice.resequence_sections(
            "line_ids", self.subsection12.id, new_parent_section_id=self.section2.id
        )
        self.assertEqual(self.subsection12.id, self.invoice["line_ids"].sorted("sequence")[4].id)

        # Subsection after subsection (other parent)
        self.invoice.resequence_sections(
            "line_ids", self.subsection12.id, previous_section_id=self.subsection11.id
        )
        self.assertEqual(self.subsection12.id, self.invoice["line_ids"].sorted("sequence")[2].id)
