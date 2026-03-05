# Copyright 2019 Creu Blanca
# Copyright 2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from markupsafe import Markup

from odoo.exceptions import ValidationError

from odoo.addons.base.tests.common import BaseCommon


class TestDocumentReference(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.page_obj = cls.env["document.page"]
        cls.history_obj = cls.env["document.page.history"]
        cls.page1 = cls.page_obj.create(
            {"name": "Test Page 1", "content": Markup("{{r2}}"), "reference": "R1"}
        )
        cls.page2 = cls.page_obj.create(
            {"name": "Test Page 1", "content": Markup("{{r1}}"), "reference": "r2"}
        )

    def test_constraints_duplicate_reference(self):
        """Should raise if reference is not unique (same as another)."""
        with self.assertRaises(ValidationError):
            self.page2.write({"reference": self.page1.reference})

    def test_constraints_invalid_reference(self):
        """Should raise if reference does not match the required pattern."""
        with self.assertRaises(ValidationError):
            self.page2.write({"reference": self.page2.reference + "-02"})

    def test_no_contrains(self):
        self.page1.write({"reference": False})
        self.assertFalse(self.page1.reference)
        self.page2.write({"reference": False})
        self.assertFalse(self.page2.reference)

    def test_check_raw(self):
        self.assertEqual(self.page2.display_name, self.page1.get_raw_content())

    def test_auto_reference(self):
        """Test if reference is proposed when saving a page without one."""
        self.assertEqual(self.page1.reference, "R1")
        new_page = self.page_obj.create(
            {"name": "Test Page with no reference", "content": "some content"}
        )
        self.assertEqual(new_page.reference, "test_page_with_no_reference")
        with self.assertRaises(ValidationError):
            new_page_duplicated_name = self.page_obj.create(
                {
                    "name": "test page with no reference",
                    "content": "<p>this should have an empty reference "
                    "because reference must be unique</p>",
                }
            )
            self.assertFalse(new_page_duplicated_name.reference)

    def test_get_formview_action(self):
        res = self.page1.get_formview_action()
        view_id = self.env.ref("document_page.view_wiki_form").id
        expected_keys = {
            "type": "ir.actions.act_window",
            "res_model": "document.page",
            "res_id": self.page1.id,
            "target": "current",
            "views": [(view_id, "form")],
        }
        for key, expected_value in expected_keys.items():
            self.assertEqual(res.get(key), expected_value, f"Mismatch in key: {key}")

    def test_compute_content_parsed(self):
        self.page1.content = Markup("<p></p>")
        self.assertEqual(self.page1.content_parsed, Markup("<p></p>"))
