# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestHasGroup(TransactionCase):
    def setUp(self):
        super(TestHasGroup, self).setUp()

        self.group0 = 'test_user_has_group.group0'
        self.group1 = 'test_user_has_group.group1'
        group0, group1 = self.env['res.groups']._load_records([
            dict(xml_id=self.group0, values={'name': 'group0'}),
            dict(xml_id=self.group1, values={'name': 'group1'}),
        ])

        self.test_user = self.env['res.users'].create({
            'login': 'testuser',
            'partner_id': self.env['res.partner'].create({
                'name': "Strawman Test User"
            }).id,
            'groups_id': [(4, group0.id, 0)]
        })

    def test_env_uid(self):
        Users = self.env['res.users'].sudo(self.test_user)
        self.assertTrue(
            Users.has_group(self.group0),
            "the test user should belong to group0"
        )
        self.assertFalse(
            Users.has_group(self.group1),
            "the test user should *not* belong to group1"
        )

    def test_record(self):
        self.assertTrue(
            self.test_user.has_group(self.group0),
            "the test user should belong to group0",
        )
        self.assertFalse(
            self.test_user.has_group(self.group1),
            "the test user shoudl not belong to group1"
        )
