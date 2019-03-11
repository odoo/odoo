# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


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

        self.grp_internal_xml_id = 'base.group_user'
        self.grp_internal = self.env.ref(self.grp_internal_xml_id)
        self.grp_portal_xml_id = 'base.group_portal'
        self.grp_portal = self.env.ref(self.grp_portal_xml_id)

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

    def test_portal_creation(self):
        grp_public = self.env.ref('base.group_public')
        grp_test_portal_xml_id = 'test_user_has_group.portal_implied_group'
        grp_test_portal = self.env['res.groups']._load_records([
            dict(xml_id=grp_test_portal_xml_id, values={'name': 'Test Group Portal'})
        ])
        grp_test_internal1 = self.env['res.groups']._load_records([
            dict(xml_id='test_user_has_group.internal_implied_group1', values={'name': 'Test Group Itnernal 1'})
        ])
        grp_test_internal2_xml_id = 'test_user_has_group.internal_implied_group2'
        grp_test_internal2 = self.env['res.groups']._load_records([
            dict(xml_id=grp_test_internal2_xml_id, values={'name': 'Test Group Internal 2'})
        ])
        self.grp_portal.implied_ids = grp_test_portal
        grp_test_internal1.implied_ids = self.grp_internal
        grp_test_internal2.implied_ids = self.grp_internal
        portal_user = self.env['res.users'].create({
            'login': 'portalTest',
            'name': 'Portal test',
            'sel_groups_%s_%s_%s' % (self.grp_internal.id, self.grp_portal.id, grp_public.id): self.grp_portal.id,
            'sel_groups_%s_%s' % (grp_test_internal1.id, grp_test_internal2.id): grp_test_internal2.id,
            })

        self.assertTrue(
            portal_user.has_group(self.grp_portal_xml_id),
            "The portal user should belong to '%s'" % self.grp_portal_xml_id,
        )
        self.assertTrue(
            portal_user.has_group(grp_test_portal_xml_id),
            "The portal user should belong to '%s'" % grp_test_portal_xml_id,
        )
        self.assertFalse(
            portal_user.has_group(grp_test_internal2_xml_id),
            "The portal user should not belong to '%s'" % grp_test_internal2_xml_id
        )
        self.assertFalse(
            portal_user.has_group(self.grp_internal_xml_id),
            "The portal user should not belong to '%s'" % self.grp_internal_xml_id
        )

    def test_portal_write(self):
        grp_remove_xml_id = 'test_portal_write.group_to_remove'
        grp_remove = self.env['res.groups']._load_records([
            dict(xml_id=grp_remove_xml_id, values={'name': 'Group to remove'})
        ])
        portal_user = self.env['res.users'].create({
            'login': 'portalTest2',
            'name': 'Portal test 2',
            'groups_id': [(6, 0, [grp_remove.id])],
            })
        grp_test_portal_xml_id = 'test_portal_write.portal_implied_group'
        grp_test_portal = self.env['res.groups']._load_records([
            dict(xml_id=grp_test_portal_xml_id, values={'name': 'Test Group Portal'})
        ])
        self.grp_portal.implied_ids = grp_test_portal
        portal_user.write({'groups_id': [(4, self.grp_portal.id, 0)]})

        self.assertFalse(
            portal_user.has_group(grp_remove_xml_id),
            "The portal user should not belong to '%s'" % grp_remove_xml_id
        )
        self.assertTrue(
            portal_user.has_group(self.grp_portal_xml_id),
            "The portal user should belong to '%s'" % self.grp_portal_xml_id,
        )
        self.assertTrue(
            portal_user.has_group(grp_test_portal_xml_id),
            "The portal user should belong to '%s'" % grp_test_portal_xml_id,
        )

    def test_two_user_types(self):
        #Create a user with two groups of user types kind (Internal and Portal)
        grp_test = self.env['res.groups']._load_records([
            dict(xml_id='test_two_user_types.implied_groups', values={'name': 'Test Group'})
        ])
        grp_test.implied_ids += self.grp_internal
        grp_test.implied_ids += self.grp_portal

        with self.assertRaises(ValidationError):
            self.env['res.users'].create({
                'login': 'test_two_user_types',
                'name': "Test User with two user types",
                'groups_id': [(6, 0, [grp_test.id])]
            })

        #Add a user with portal to the group Internal
        test_user = self.env['res.users'].create({
                'login': 'test_user_portal',
                'name': "Test User with two user types",
                'groups_id': [(6, 0, [self.grp_portal.id])]
             })
        with self.assertRaises(ValidationError):
            self.grp_internal.users = [(4, test_user.id)]
