# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.tests import new_test_user

from odoo.addons.base.tests.common import BaseCommon


class TestDocumentPageAccessGroupBase(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.env["res.groups"].create({"name": "Test group"})
        cls.user = new_test_user(
            cls.env, login="test-user", groups="document_knowledge.group_document_user"
        )
        cls.manager_user = new_test_user(
            cls.env,
            login="test-manager-user",
            groups="document_knowledge.group_document_user",
        )
        cls.manager_user.write({"group_ids": [Command.link(cls.group.id)]})
        cls.public_page = cls.env["document.page"].create(
            {"name": "Public Page", "type": "content"}
        )
        cls.knowledge_page = cls.env["document.page"].create(
            {
                "name": "Knowledge Page",
                "type": "content",
                "groups_id": [Command.set([cls.group.id])],
            }
        )
        cls.user_page = cls.env["document.page"].create(
            {
                "name": "User Page (basic user)",
                "type": "content",
                "user_ids": [Command.set([cls.user.id])],
            }
        )
