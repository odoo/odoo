# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import common


class TestDocumentPage(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.page_obj = self.env["document.page"]
        self.history_obj = self.env["document.page.history"]
        self.category1 = self.env.ref("document_page.demo_category1")
        self.page1 = self.env.ref("document_page.demo_page1")

    def test_page_creation(self):
        page = self.page_obj.create(
            {
                "name": "Test Page 1",
                "parent_id": self.category1.id,
                "content": "<p>Test content</p>",
            }
        )
        self.assertEqual(page.content, "<p>Test content</p>")
        self.assertEqual(len(page.history_ids), 1)
        page.content = "<p>New content for Demo Page</p>"
        self.assertEqual(len(page.history_ids), 2)

    def test_category_template(self):
        page = self.page_obj.create(
            {"name": "Test Page 2", "parent_id": self.category1.id}
        )
        page._onchange_parent_id()
        self.assertEqual(page.content, self.category1.template)

    def test_page_history_diff(self):
        page = self.page_obj.create(
            {"name": "Test Page 3", "content": "<div>Test content</div>"}
        )
        page.content = "<div>New content</div>"
        self.assertIsNotNone(page.history_ids[0].diff)

    def test_page_link(self):
        page = self.page_obj.create(
            {"name": "Test Page 3", "content": "<div>Test content</div>"}
        )
        self.assertEqual(
            page.backend_url,
            f"/web#id={page.id}&model=document.page&view_type=form",
        )
        menu = self.env.ref("document_knowledge.menu_document")
        page.menu_id = menu
        self.assertEqual(
            page.backend_url,
            f"/web#id={page.id}&model=document.page&view_type=form&action={menu.action.id}",
        )

    def test_page_copy(self):
        page = self.page_obj.create(
            {"name": "Test Page 3", "content": "<div>Test content</div>"}
        )
        page_copy = page.copy()
        self.assertEqual(page_copy.name, page.name + " (copy)")
        self.assertEqual(page_copy.content, page.content)
        self.assertEqual(page_copy.draft_name, "1.0")
        self.assertEqual(page_copy.draft_summary, "summary")
