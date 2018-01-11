# -*- coding: utf-8 -*-
import openerp.tests

class TestHasGroup(openerp.tests.TransactionCase):
    def setUp(self):
        super(TestHasGroup, self).setUp()

        group0 = self.env['ir.model.data']._update(
            'res.groups', 'test_user_has_group',
            {'name': 'group0'},
            xml_id='group0'
        )
        self.group0 = 'test_user_has_group.group0'
        self.env['ir.model.data']._update(
            'res.groups', 'test_user_has_group',
            {'name': 'group1'},
            xml_id='group1'
        )
        self.group1 = 'test_user_has_group.group1'

        self.test_user = self.env['res.users'].create({
            'login': 'testuser',
            'partner_id': self.env['res.partner'].create({
                'name': "Strawman Test User"
            }).id,
            'groups_id': [(4, group0, 0)]
        })

    def test_old_api(self):
        Users = self.registry['res.users']

        self.assertTrue(
            Users.has_group(self.cr, self.test_user.id, self.group0),
            "the test user should belong to group0"
        )
        self.assertFalse(
            Users.has_group(self.cr, self.test_user.id, self.group1),
            "the test user should *not* belong to group1"
        )

    def test_new_api(self):
        self.assertTrue(
            self.test_user.has_group(self.group0),
            "the test user should belong to group0",
        )
        self.assertFalse(
            self.test_user.has_group(self.group1),
            "the test user shoudl not belong to group1"
        )
