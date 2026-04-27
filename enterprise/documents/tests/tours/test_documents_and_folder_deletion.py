# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="


@tagged("post_install", "-at_install")
class TestDocumentDeletion(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.folder = cls.env["documents.document"].create({
            "type": "folder",
            "name": "Folder1",
            "owner_id": cls.env.ref('base.user_root').id,
            "access_internal": "edit",
            "children_ids": [
                Command.create(
                    {
                        "datas": GIF,
                        "name": "Chouchou",
                        "mimetype": "image/gif",
                        "owner_id": cls.env.user.id,
                    }
                )
            ],
        })
        cls.document = cls.folder.children_ids[0]

    def test_delete_folder_and_documents_tour(self):
        folder_copy = self.folder
        document_copy = self.document
        self.start_tour(
            f"/odoo/documents/{self.document.access_token}", 'document_delete_tour', login='admin')
        self.assertTrue(folder_copy.exists(), "The folder should still exist")
        self.assertFalse(document_copy.exists(), "The document should not exist anymore")

    def test_tour_default_action_view(self):
        # todo: move to a more appropriate place in master
        self.start_tour(
            f"/odoo/documents.document/{self.document.id}", 'document_default_access_view',
            login='admin'
        )
