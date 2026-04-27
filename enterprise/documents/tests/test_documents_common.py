import base64

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
TEXT = base64.b64encode(bytes("TEST", 'utf-8'))


class TransactionCaseDocuments(TransactionCase):
    def _assert_no_members(self, documents):
        self.assertFalse(documents.access_ids.filtered('role'),
                         "There shouldn't be any access records with role for these documents.")

    def _assert_raises_check_access_rule(self, document, operation=None, msg=None):
        operations = [operation] if operation else ('read', 'write')
        for operation in operations:
            with self.subTest(operation=operation, msg=msg):
                with self.assertRaises(AccessError):
                    document.check_access(operation)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.document_manager, cls.doc_user, cls.internal_user, cls.portal_user, cls.public_user, = cls.env['res.users'].create([
            {
                'email': "dtdm@yourcompany.com",
                'groups_id': [Command.link(cls.env.ref('documents.group_documents_manager').id)],
                'login': "dtdm",
                'name': "Documents Manager",
            }, {
                'email': 'documents@example.com',
                'groups_id': [Command.link(cls.env.ref('documents.group_documents_user').id)],
                'login': 'documents@example.com',
                'name': 'Documents User',
            }, {
                'login': 'internal_user',
                'groups_id': [Command.link(cls.env.ref('base.group_user').id)],
                'name': 'Internal user'
            }, {
                'login': 'portal_user',
                'groups_id': [Command.link(cls.env.ref('base.group_portal').id)],
                'name': 'Portal user'
            }, {
                'login': 'public_user',
                'groups_id': [Command.link(cls.env.ref('base.group_public').id)],
                'name': 'Public user',
            },
        ])
        cls.odoobot = cls.env.ref('base.user_root')
        cls.folder_a, cls.folder_b = cls.env['documents.document'].create([
            {
                'type': 'folder',
                'name': f'folder {letter}',
                'owner_id': cls.doc_user.id,
                'access_internal': 'view',
            } for letter in ('A', 'B')
        ])
        cls.folder_a_a = cls.env['documents.document'].create({
            'type': 'folder',
            'name': 'folder A - A',
            'folder_id': cls.folder_a.id,
            'owner_id': cls.doc_user.id,
        })
        cls.tag_b = cls.env['documents.tag'].create({
            'name': "categ_b > tag_b",
        })
        cls.tag_a, cls.tag_a_a = cls.env['documents.tag'].create([
            {'name': 'tag_a'},
            {'name': 'tag_a_a'},
        ])
        cls.document_gif = cls.env['documents.document'].create({
            'type': 'binary',
            'datas': GIF,
            'name': 'file.gif',
            'mimetype': 'image/gif',
            'folder_id': cls.folder_b.id,
            'owner_id': cls.doc_user.id,
        })
        cls.document_txt = cls.env['documents.document'].create({
            'type': 'binary',
            'datas': TEXT,
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': cls.folder_b.id,
            'owner_id': cls.doc_user.id,
        })
        cls.document_txt.access_via_link = "view"

        cls.server_action = cls.env['ir.actions.server'].create({
            'name': 'Add tag_a',
            'model_id': cls.env.ref('documents.model_documents_document').id,
            'type': 'ir.actions.server',
            'groups_id': cls.env.ref('base.group_user').ids,
            'update_path': 'tag_ids',
            'usage': 'ir_actions_server',
            'state': 'object_write',
            'update_m2m_operation': 'add',
            'resource_ref': f'documents.tag,{cls.tag_a.id}',
        })
