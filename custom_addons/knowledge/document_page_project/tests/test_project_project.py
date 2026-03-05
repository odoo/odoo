# Copyright (C) 2021 TREVI Software
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import common


class TestProjectProject(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Page = cls.env["document.page"]
        cls.Project = cls.env["project.project"]
        cls.default_page = cls.Page.create({"name": "My page"})

    def test_page_count(self):
        proj = self.Project.create({"name": "Proj A"})

        self.assertEqual(
            proj.document_page_count, 0, "Initial page count should be zero"
        )

        self.default_page.project_id = proj
        proj._compute_document_page_count()

        self.assertEqual(
            proj.document_page_count,
            1,
            "After attaching project to document the page count should be one",
        )
        self.assertIn(
            self.default_page,
            proj.document_page_ids,
            "The page should be in the list of document pages for project",
        )
