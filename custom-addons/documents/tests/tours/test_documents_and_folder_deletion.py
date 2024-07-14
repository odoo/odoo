# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import HttpCase

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="

@tagged("post_install", "-at_install")
class TestDocumentDeletion(HttpCase):

    def test_delete_folder_and_documents_tour(self):
        folder = self.env['documents.folder'].create({
            "name": "Workspace1",
        })
        document = self.env['documents.document'].create({
            'datas': GIF,
            "name": "Chouchou",
            "folder_id": folder.id,
            'mimetype': 'image/gif',
        })
        folder_copy = folder
        document_copy = document
        self.start_tour("/web", 'document_delete_tour', login='admin')
        self.assertFalse(folder_copy.exists(), "The folder should not exist anymore")
        self.assertFalse(document_copy.exists(), "The document should not exist anymore")
