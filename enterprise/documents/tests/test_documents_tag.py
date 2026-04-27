# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestTags(TransactionCase):

    def test_create_tag(self):
        tag = self.env['documents.tag'].create({'name': 'Foo'})
        self.assertTrue(tag.sequence > 0, 'should have a non-zero sequence')

    def test_remove_tag(self):
        tag, used_tag = self.env['documents.tag'].create([{'name': 'Foo'}, {'name': 'Used Tag'}])

        self.env['ir.model.data'].create({
            'name': 'used_tag',
            'module': 'documents',
            'model': 'documents.tag',
            'res_id': used_tag.id,
        })
        action_server = self.env['ir.actions.server'].create({
            'name': 'Test Action',
            'model_id': self.env['ir.model']._get_id('documents.document'),
            'update_path': 'tag_ids',
            'usage': 'ir_actions_server',
            'state': 'object_write',
            'update_m2m_operation': 'add',
            'resource_ref': 'documents.tag,%s' % used_tag.id
        })

        tag.unlink()
        self.assertFalse(tag.exists(), "Tag 'Foo' should be deleted.")
        with self.assertRaises(UserError, msg="Used Tag should not be deletable as it's used in a server action."):
            used_tag.unlink()
            
        action_server.unlink()
        used_tag.unlink()
        self.assertFalse(used_tag.exists(), "Formerly used tag should be deleted if server action has been deleted.")
