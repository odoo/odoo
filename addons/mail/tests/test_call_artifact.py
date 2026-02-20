# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestCallArtifact(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_member = cls.env['res.users'].create({
            'name': 'Member User',
            'login': 'member_user',
            'group_ids': [Command.set([cls.env.ref('base.group_user').id])],
        })
        cls.user_non_member = cls.env['res.users'].create({
            'name': 'Non Member User',
            'login': 'non_member_user',
            'group_ids': [Command.set([cls.env.ref('base.group_user').id])],
        })
        cls.admin_user = cls.env['res.users'].create({
            'name': 'Admin User',
            'login': 'admin_user',
            'group_ids': [Command.set([cls.env.ref('base.group_erp_manager').id])],
        })

        cls.channel = cls.env['discuss.channel'].create({
            'name': 'Test Channel',
            'channel_type': 'channel',
        })
        cls.channel.add_members(partner_ids=[cls.user_member.partner_id.id])

        cls.call = cls.env['discuss.call.history'].create({
            'channel_id': cls.channel.id,
            'start_dt': fields.Datetime.now(),
        })

        cls.artifact = cls.env['call.artifact'].create({
            'discuss_call_history_id': cls.call.id,
            'start_ms': 0,
            'end_ms': 1000,
        })

    def test_discuss_artifact_overlap(self):
        # Already have one at 0-1000 from setUpClass
        # 1.  No overlap -> OK
        self.env['call.artifact'].create({'discuss_call_history_id': self.call.id, 'start_ms': 2000, 'end_ms': 3000})

        # 2. Non significant overlap -> OK
        self.env['call.artifact'].create({'discuss_call_history_id': self.call.id, 'start_ms': 2600, 'end_ms': 3600})

        # 3. Significant overlap -> Error
        with self.assertRaises(ValidationError):
            self.env['call.artifact'].create({'discuss_call_history_id': self.call.id, 'start_ms': 3000, 'end_ms': 4000})

    def test_user_access_member(self):
        """ Member of the channel should be able to read the artifact """
        artifact = self.artifact.with_user(self.user_member)
        # Check Read Access
        self.assertTrue(artifact.read(['start_ms']), "Channel member should be able to read artifact")

        # Check Search Access
        search_res = self.env['call.artifact'].with_user(self.user_member).search([('id', '=', self.artifact.id)])
        self.assertEqual(len(search_res), 1, "Channel member should be able to find artifact")

        # Check Write Access (Should be False)
        with self.assertRaises(AccessError):
            artifact.write({'end_ms': 2000})

        # Check Create Access (Should be False)
        with self.assertRaises(AccessError):
            self.env['call.artifact'].with_user(self.user_member).create({
                'discuss_call_history_id': self.call.id,
                'start_ms': 2000,
                'end_ms': 3000,
            })

        # Check Unlink Access (Should be False)
        with self.assertRaises(AccessError):
            artifact.unlink()

    def test_user_access_non_member(self):
        """ Non-member of the channel should NOT be able to read the artifact """
        artifact = self.artifact.with_user(self.user_non_member)

        # Check Read Access
        with self.assertRaises(AccessError):
            artifact.read(['start_ms'])

        # Check Search Access
        search_res = self.env['call.artifact'].with_user(self.user_non_member).search([('id', '=', self.artifact.id)])
        self.assertEqual(len(search_res), 0, "Non-member should not find artifact")

    def test_admin_access(self):
        """ Admin should have full access """
        artifact = self.artifact.with_user(self.admin_user)

        # Check Read Access
        self.assertTrue(artifact.read(['start_ms']), "Admin should be able to read artifact")

        # Check Write Access
        artifact.write({'end_ms': 2000})
        self.assertEqual(artifact.end_ms, 2000, "Admin should be able to write artifact")

        # Check Create Access
        new_artifact = self.env['call.artifact'].with_user(self.admin_user).create({
            'discuss_call_history_id': self.call.id,
            'start_ms': 5000,
            'end_ms': 6000,
        })
        self.assertTrue(new_artifact, "Admin should be able to create artifact")

        # Check Unlink Access
        new_artifact.unlink()
        self.assertFalse(new_artifact.exists(), "Admin should be able to unlink artifact")
