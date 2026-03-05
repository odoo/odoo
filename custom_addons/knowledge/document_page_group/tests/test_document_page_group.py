# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.base.tests.common import BaseCommon


class TestDocumentPageGroup(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        knowledge_group = cls.env.ref("document_knowledge.group_document_user").id
        cls.user_id = cls.env["res.users"].create(
            {
                "name": "user",
                "login": "login",
                "email": "email",
                "group_ids": [Command.link(knowledge_group)],
            }
        )
        cls.group = cls.env.ref("document_page.group_document_manager")

        cls.categ_1 = cls.env["document.page"].create(
            {"name": "Categ 1", "type": "category"}
        )
        cls.categ_2 = cls.env["document.page"].create(
            {"name": "Categ 2", "type": "category", "parent_id": cls.categ_1.id}
        )
        cls.page = cls.env["document.page"].create(
            {"name": "Page 1", "type": "content", "parent_id": cls.categ_1.id}
        )

    def test_document_page_group(self):
        pages = (
            self.env["document.page"]
            .with_user(user=self.user_id.id)
            .search([("type", "=", "content")])
        )
        self.assertIn(self.page.id, pages.ids)

        self.categ_1.write({"direct_group_ids": [Command.link(self.group.id)]})
        self.assertIn(self.group.id, self.categ_2.group_ids.ids)

        pages = (
            self.env["document.page"]
            .with_user(user=self.user_id.id)
            .search([("type", "=", "content")])
        )
        self.assertNotIn(self.page.id, pages.ids)
