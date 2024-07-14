# -*- coding: utf-8 -*-

import base64

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import mute_logger

from psycopg2 import IntegrityError


class TestCaseSecurity(TransactionCase):

    def setUp(self):
        super(TestCaseSecurity, self).setUp()
        self.arbitrary_group = self.env['res.groups'].create({
            'name': 'arbitrary_group',
            'implied_ids': [(6, 0, [self.ref('base.group_user')])],
        })

        self.basic_user = self.env['res.users'].create({
            'name': "documents test basic user",
            'login': "dtbu",
            'email': "dtbu@yourcompany.com",
            'groups_id': [(6, 0, [self.ref('base.group_user')])]
        })
        self.document_user = self.env['res.users'].create({
            'name': "documents test documents user",
            'login': "dtdu",
            'email': "dtdu@yourcompany.com",
            'groups_id': [(6, 0, [self.ref('documents.group_documents_user')])]
        })
        self.test_group_user = self.env['res.users'].create({
            'name': "documents test group user",
            'login': "dtgu",
            'email': "dtgu@yourcompany.com",
            'groups_id': [(6, 0, [self.arbitrary_group.id])]
        })
        self.test_group_user2 = self.env['res.users'].create({
            'name': "documents test group user2",
            'login': "dtgu2",
            'email': "dtgu2@yourcompany.com",
            'groups_id': [(6, 0, [self.arbitrary_group.id])]
        })
        self.document_manager = self.env['res.users'].create({
            'name': "documents test documents manager",
            'login': "dtdm",
            'email': "dtdm@yourcompany.com",
            'groups_id': [(6, 0, [self.ref('documents.group_documents_manager')])]
        })

    def test_documents_access_default(self):
        """
        Tests the access rights for a document where no access_group is specified
        users should default in read/write.
        """

        folder_d = self.env['documents.folder'].create({
            'name': 'folder D',
        })
        document_d = self.env['documents.document'].create({
            'name': 'document D',
            'folder_id': folder_d.id,
        })

        expected_read_result = [{'id': document_d.id, 'name': 'document D'}]

        basic_user_doc_d_read_result = document_d.with_user(self.basic_user).read(['name'])
        self.assertEqual(basic_user_doc_d_read_result, expected_read_result,
                         'test_group_user should be able to read document_d')
        doc_d_read_result = document_d.with_user(self.document_user).read(['name'])
        self.assertEqual(doc_d_read_result, expected_read_result,
                         'document_user should be able to read document_d')

        document_d.with_user(self.basic_user).write({'name': 'basic_user_write'})
        self.assertEqual(document_d.name, 'basic_user_write')
        document_d.with_user(self.document_user).write({'name': 'document_user_write'})
        self.assertEqual(document_d.name, 'document_user_write')
        document_d.with_user(self.test_group_user).write({'name': 'user_write'})
        self.assertEqual(document_d.name, 'user_write')
        document_d.with_user(self.document_manager).write({'name': 'document_manager_write'})
        self.assertEqual(document_d.name, 'document_manager_write')

    def test_documents_access_manager_read_write(self):
        """
        Tests the access rights for a document where group_documents_manager is the only group with access (read/write).
        """

        folder_a = self.env['documents.folder'].create({
            'name': 'folder A',
            'group_ids': [(6, 0, [self.ref('documents.group_documents_manager')])],
        })

        document_a = self.env['documents.document'].create({
            'name': 'document A',
            'folder_id': folder_a.id,
        })

        with self.assertRaises(AccessError):
            document_a.with_user(self.basic_user).read()
        with self.assertRaises(AccessError):
            document_a.with_user(self.test_group_user).read()
        with self.assertRaises(AccessError):
            document_a.with_user(self.document_user).read()
        with self.assertRaises(AccessError):
            document_a.with_user(self.basic_user).write({'name': 'nameChangedA'})
        with self.assertRaises(AccessError):
            document_a.with_user(self.test_group_user).write({'name': 'nameChangedA'})
        with self.assertRaises(AccessError):
            document_a.with_user(self.document_user).write({'name': 'nameChangedA'})

        document_a.with_user(self.document_manager).write({'name': 'nameChangedManagerA'})
        self.assertEqual(document_a.name, 'nameChangedManagerA',
                         'document manager should be able to write document_a')

    def test_documents_access_arbitrary_readonly(self):
        """
        Tests the access rights for a document where arbitrary_group is the only group with access (read).
        """
        
        folder_b = self.env['documents.folder'].create({
            'name': 'folder B',
            'read_group_ids': [(6, 0, [self.arbitrary_group.id])],
        })
        document_b = self.env['documents.document'].create({
            'name': 'document B',
            'folder_id': folder_b.id,
        })

        with self.assertRaises(AccessError):
            document_b.with_user(self.basic_user).read()
        with self.assertRaises(AccessError):
            document_b.with_user(self.document_user).read()
        with self.assertRaises(AccessError):
            document_b.with_user(self.basic_user).write({'name': 'nameChangedB'})
        with self.assertRaises(AccessError):
            document_b.with_user(self.document_user).write({'name': 'nameChangedB'})
        with self.assertRaises(AccessError):
            document_b.with_user(self.test_group_user).write({'name': 'nameChangedB'})

        document_b.with_user(self.test_group_user).toggle_favorited()
        self.assertFalse(document_b.is_favorited)

        test_group_user_document_b_name = document_b.with_user(self.test_group_user).read(['name'])
        self.assertEqual(test_group_user_document_b_name, [{'id': document_b.id, 'name': 'document B'}],
                         'test_group_user should be able to read document_b')

    def test_documents_arbitrary_read_write(self):
        """
        Tests the access rights for a document where arbitrary_group is the only group with access (read/write).
        The group_documents_manager always keeps the read/write access.
        """

        folder_c = self.env['documents.folder'].create({
            'name': 'folder C',
            'group_ids': [(6, 0, [self.arbitrary_group.id])],
        })
        document_c = self.env['documents.document'].create({
            'name': 'document C',
            'folder_id': folder_c.id,
        })

        with self.assertRaises(AccessError):
            document_c.with_user(self.basic_user).read()
        with self.assertRaises(AccessError):
            document_c.with_user(self.document_user).read()
        with self.assertRaises(AccessError):
            document_c.with_user(self.basic_user).write({'name': 'nameChangedC'})
        with self.assertRaises(AccessError):
            document_c.with_user(self.document_user).write({'name': 'nameChangedC'})

        document_c.with_user(self.test_group_user).write({'name': 'nameChanged'})
        self.assertEqual(document_c.name, 'nameChanged',
                         'test_group_user should be able to write document_c')
        document_c.with_user(self.document_manager).write({'name': 'nameChangedManager'})
        self.assertEqual(document_c.name, 'nameChangedManager',
                         'document manager should be able to write document_c')

    def test_documents_access(self):
        """
        Tests the access rights for a document where 'user_specific' is True.
        Users should be limited to records for which they are the owner only if they are limited to read.
        """

        arbitrary_group2 = self.env['res.groups'].create({
            'name': 'arbitrary_group2',
            'implied_ids': [(6, 0, [self.ref('base.group_user')])],
        })
        test_group2_user = self.env['res.users'].create({
            'name': "documents test group user21",
            'login': "dtgu21",
            'email': "dtgu21@yourcompany.com",
            'groups_id': [(6, 0, [arbitrary_group2.id])]
        })
        folder_owner = self.env['documents.folder'].create({
            'name': 'folder owner',
            'group_ids': [(6, 0, [self.arbitrary_group.id])],
            'read_group_ids': [(6, 0, [arbitrary_group2.id])],
            'user_specific': True,
        })
        document_owner = self.env['documents.document'].create({
            'name': 'document owner',
            'folder_id': folder_owner.id,
            'owner_id': self.test_group_user.id,
        })
        document_owner2 = self.env['documents.document'].create({
            'name': 'document owner2',
            'folder_id': folder_owner.id,
            'owner_id': self.test_group_user2.id,
        })
        document_not_owner = self.env['documents.document'].create({
            'name': 'document not owner',
            'folder_id': folder_owner.id,
        })
        document_read_owner = self.env['documents.document'].create({
            'name': 'document read owner',
            'folder_id': folder_owner.id,
            'owner_id': test_group2_user.id,
        })


        # documents access by owner
        with self.assertRaises(AccessError):
            document_not_owner.with_user(self.basic_user).read()
        with self.assertRaises(AccessError):
            document_not_owner.with_user(test_group2_user).read()
        with self.assertRaises(AccessError):
            document_not_owner.with_user(self.document_user).read()
        with self.assertRaises(AccessError):
            document_not_owner.with_user(self.basic_user).write({'name': 'nameChangedA'})
        with self.assertRaises(AccessError):
            document_not_owner.with_user(self.document_user).write({'name': 'nameChangedA'})

        with self.assertRaises(AccessError):
            document_owner.with_user(self.basic_user).read()
        with self.assertRaises(AccessError):
            document_owner.with_user(self.document_user).read()
        with self.assertRaises(AccessError):
            document_owner.with_user(test_group2_user).read()
        with self.assertRaises(AccessError):
            document_owner.with_user(self.basic_user).write({'name': 'nameChangedA'})
        with self.assertRaises(AccessError):
            document_owner.with_user(self.document_user).write({'name': 'nameChangedA'})

        with self.assertRaises(AccessError):
            document_owner2.with_user(test_group2_user).read()

        name_from_read_owner = document_read_owner.with_user(test_group2_user).name
        self.assertEqual(name_from_read_owner, document_read_owner.name,
                         'test_group2_user should be able to read his own document')

        document_owner.with_user(self.test_group_user).write({'name': 'nameChangedOwner'})
        self.assertEqual(document_owner.name, 'nameChangedOwner',
                         'test_group_user should be able to write document_owner')
        document_from_user = self.env['documents.document'].with_user(self.test_group_user).browse(
            document_not_owner.id)
        self.assertEqual(document_from_user.name, 'document not owner',
                         'test_group_user should be able to read document_not_owner as he is in the write group')
        document_not_owner.with_user(self.test_group_user).write({'name': 'nameChangedA'})
        self.assertEqual(document_not_owner.name, 'nameChangedA',
                         'test_group_user should be able to write document_not_owner as he is in the write group')

        # We now set the document to user_specific for write permissions.
        folder_owner.user_specific_write = True
        # since the user is not in the folder's write group, they will not be able to write the documents
        with self.assertRaises(AccessError):
            document_read_owner.with_user(test_group2_user).write({'name': 'nameChange'})
        # the first user is in the write groups but is not the owner of the document
        with self.assertRaises(AccessError):
            document_read_owner.with_user(self.test_group_user).write({'name': 'nameChange'})

        # Now give the right group to test_group2_user.
        test_group2_user.groups_id += self.arbitrary_group
        # they should now be able to write on the document
        document_read_owner.with_user(test_group2_user).write({'name': 'nameChangedC'})

    def test_share_link_access(self):
        """
        Tests access rights for share links when the access rights of the folder is changed after the creation of the link.
        """

        folder_share = self.env['documents.folder'].create({
            'name': 'folder share',
        })
        document = self.env['documents.document'].create({
            'datas': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file.gif',
            'mimetype': 'image/gif',
            'folder_id': folder_share.id,
        })
        test_share = self.env['documents.share'].with_user(self.document_user).create({
            'folder_id': folder_share.id,
            'type': 'ids',
            'document_ids': [(6, 0, [document.id])]
        })
        available_documents = test_share._get_documents_and_check_access(test_share.access_token, operation='read')
        self.assertEqual(len(available_documents), 1,
                         'This method should indicate that the create_uid has access to the folder')
        folder_share.write({'group_ids': [(6, 0, [self.ref('documents.group_documents_manager')])]})
        available_documents = test_share._get_documents_and_check_access(test_share.access_token, operation='read')
        self.assertEqual(len(available_documents), 0,
                         'This method should indicate that the create_uid doesnt have access to the folder anymore')

    def test_share_link_dynamic_access(self):
        """
        Test the dynamic change of documents available from share links when access conditions change.
        """

        TEXT = base64.b64encode(bytes("TEST", 'utf-8'))
        folder_share = self.env['documents.folder'].create({
            'name': 'folder share',
            'read_group_ids': [(6, 0, [self.ref('documents.group_documents_user')])]
        })
        document_a = self.env['documents.document'].create({
            'datas': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'owner_id': self.document_manager.id,
            'name': 'filea.gif',
            'mimetype': 'image/gif',
            'folder_id': folder_share.id,
        })
        document_b = self.env['documents.document'].create({
            'datas': TEXT,
            'owner_id': self.document_manager.id,
            'name': 'fileb.gif',
            'mimetype': 'image/gif',
            'folder_id': folder_share.id,
        })
        document_c = self.env['documents.document'].create({
            'datas': TEXT,
            'owner_id': self.document_user.id,
            'name': 'filec.gif',
            'mimetype': 'image/gif',
            'folder_id': folder_share.id,
        })
        test_share = self.env['documents.share'].with_user(self.document_user).create({
            'folder_id': folder_share.id,
            'type': 'ids',
            'document_ids': [(6, 0, [document_a.id, document_b.id, document_c.id])]
        })
        available_documents = test_share._get_documents_and_check_access(test_share.access_token, operation='read')
        self.assertEqual(len(available_documents), 3, "there should be 3 available documents")

        folder_share.write({'user_specific': True})
        available_documents = test_share._get_documents_and_check_access(test_share.access_token, operation='read')
        self.assertEqual(len(available_documents), 1, "there should be 1 available document")
        self.assertEqual(available_documents.name, 'filec.gif', "the document C should be available")

    def test_share_parent_folder_with_ids(self):
        """
        Tests the access rights of a share link when the parent folder is shared with ids.
        """
        TEXT = base64.b64encode(bytes("TEST", 'utf-8'))
        folder_share_parent = self.env['documents.folder'].create({
            'name': 'folder share',
            'read_group_ids': [(6, 0, [self.ref('documents.group_documents_user')])]
        })
        folder_share_child_a = self.env['documents.folder'].create({
            'name': 'folder share',
            'parent_folder_id': folder_share_parent.id,
            'read_group_ids': [(6, 0, [self.ref('documents.group_documents_user')])]
        })
        folder_share_child_b = self.env['documents.folder'].create({
            'name': 'folder share',
            'parent_folder_id': folder_share_parent.id,
            'read_group_ids': [(6, 0, [self.ref('documents.group_documents_user')])]
        })
        document_a = self.env['documents.document'].create({
            'datas': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'owner_id': self.document_manager.id,
            'name': 'filea.gif',
            'mimetype': 'image/gif',
            'folder_id': folder_share_child_a.id,
        })
        document_b = self.env['documents.document'].create({
            'datas': TEXT,
            'owner_id': self.document_manager.id,
            'name': 'fileb.gif',
            'mimetype': 'image/gif',
            'folder_id': folder_share_child_b.id,
        })
        test_share = self.env['documents.share'].with_user(self.document_user).create({
            'folder_id': folder_share_parent.id,
            'type': 'ids',
            'document_ids': [(6, 0, [document_a.id, document_b.id])]
        })

        available_documents = test_share._get_documents_and_check_access(test_share.access_token, operation='read')
        self.assertEqual(len(available_documents), 2, "there should be 2 available documents")

    def test_folder_user_specific_write(self):
        """
        Tests that `user_specific_write` is disabled when `user_specific` is disabled
        """
        folder = self.env['documents.folder'].create({
            'name': 'Test Folder',
            'user_specific': True,
            'user_specific_write': True,
        })

        folder.user_specific = False
        self.assertFalse(folder.user_specific_write)

        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                with self.cr.savepoint():
                    folder.write({'user_specific_write': True})

    def test_folder_has_write_access(self):
        """
        Tests that user has right write  access for folder using `has_write_access`.
        """

        # No groups on folder
        folder = self.env['documents.folder'].create({
            'name': 'Test Folder',
        })

        self.assertTrue(folder.with_user(self.document_manager).has_write_access, "Document manager should have write access on folder")
        self.assertTrue(folder.with_user(self.document_user).has_write_access, "Document user should have write access on folder")

        # manager can write and arbitary group can read
        folder.write({
            'group_ids': [(6, 0, [self.ref('documents.group_documents_manager')])],
            'read_group_ids': [(6, 0, [self.arbitrary_group.id])],
        })
        self.assertTrue(folder.with_user(self.document_manager).has_write_access, "Document manager should have write access on folder")
        self.assertFalse(folder.with_user(self.document_user).has_write_access, "Document user should not have write access on folder")

    def test_link_constrains(self):
        folder = self.env['documents.folder'].create({'name': 'folder'})
        for url in ("wrong URL format", "https:/ example.com", "test https://example.com"):
            with self.assertRaises(ValidationError):
                self.env['documents.document'].create({
                    'name': 'Test Document',
                    'folder_id': folder.id,
                    'url': url,
                })
