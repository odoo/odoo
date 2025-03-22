# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo import Command


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
            'groups_id': [Command.set([group0.id])]
        })

        self.grp_internal_xml_id = 'base.group_user'
        self.grp_internal = self.env.ref(self.grp_internal_xml_id)
        self.grp_portal_xml_id = 'base.group_portal'
        self.grp_portal = self.env.ref(self.grp_portal_xml_id)
        self.grp_public_xml_id = 'base.group_public'
        self.grp_public = self.env.ref(self.grp_public_xml_id)

    def test_env_uid(self):
        Users = self.env['res.users'].with_user(self.test_user)
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
        """Here we check that portal user creation fails if it tries to create a user
           who would also have group_user by implied_group.
           Otherwise, it succeeds with the groups we asked for.
        """
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

        grp_test_internal1.implied_ids = False
        grp_test_internal2.implied_ids = False

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
        self.assertTrue(
            portal_user.has_group(grp_test_internal2_xml_id),
            "The portal user should belong to '%s'" % grp_test_internal2_xml_id
        )
        self.assertFalse(
            portal_user.has_group(self.grp_internal_xml_id),
            "The portal user should not belong to '%s'" % self.grp_internal_xml_id
        )

        portal_user.unlink()  # otherwise, badly modifying the implication would raise

        grp_test_internal1.implied_ids = self.grp_internal
        grp_test_internal2.implied_ids = self.grp_internal

        with self.assertRaises(ValidationError): # current group implications forbid to create a portal user
            portal_user = self.env['res.users'].create({
                'login': 'portalFail',
                'name': 'Portal fail',
                'sel_groups_%s_%s_%s' % (self.grp_internal.id, self.grp_portal.id, grp_public.id): self.grp_portal.id,
                'sel_groups_%s_%s' % (grp_test_internal1.id, grp_test_internal2.id): grp_test_internal2.id,
            })

    def test_portal_write(self):
        """Check that adding a new group to a portal user works as expected,
           except if it implies group_user/public, in chich case it should raise.
        """
        grp_test_portal = self.env["res.groups"].create({"name": "implied by portal"})
        self.grp_portal.implied_ids = grp_test_portal

        portal_user = self.env['res.users'].create({
            'login': 'portalTest2',
            'name': 'Portal test 2',
            'groups_id': [Command.set([self.grp_portal.id])],
            })

        self.assertEqual(
            portal_user.groups_id, (self.grp_portal + grp_test_portal),
            "The portal user should have the implied group.",
        )

        grp_fail = self.env["res.groups"].create(
            {"name": "fail", "implied_ids": [Command.set([self.grp_internal.id])]})

        with self.assertRaises(ValidationError):
            portal_user.write({'groups_id': [Command.link(grp_fail.id)]})

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
                'groups_id': [Command.set([grp_test.id])]
            })

        #Add a user with portal to the group Internal
        test_user = self.env['res.users'].create({
                'login': 'test_user_portal',
                'name': "Test User with two user types",
                'groups_id': [Command.set([self.grp_portal.id])]
             })
        with self.assertRaises(ValidationError):
            self.grp_internal.users = [Command.link(test_user.id)]

    def test_two_user_types_implied_groups(self):
        """Contrarily to test_two_user_types, we simply add an implied_id to a group.
           This will trigger the addition of the relevant users to the relevant groups;
           if, say, this was done in SQL and thus bypassing the ORM, it would bypass the constraints
           and field recomputations, and thus give us a case uncovered by the aforementioned test.
        """
        grp_test = self.env["res.groups"].create(
            {"name": "test", "implied_ids": [Command.set([self.grp_internal.id])]})

        test_user = self.env['res.users'].create({
            'login': 'test_user_portal',
            'name': "Test User with one user types",
            'groups_id': [Command.set([grp_test.id])]
        })

        with self.assertRaisesRegex(ValidationError, "The user cannot have more than one user types"), self.env.cr.savepoint():
            grp_test.write({'implied_ids': [Command.link(self.grp_portal.id)]})

        self.env["ir.model.fields"].create(
            {
                "name": "x_group_names",
                "model_id": self.env.ref("base.model_res_users").id,
                "state": "manual",
                "field_description": "A computed field that depends on groups_id",
                "compute": "for r in self: r['x_group_names'] = ', '.join(r.groups_id.mapped('name'))",
                "depends": "groups_id",
                "store": True,
                "ttype": "char",
            }
        )
        self.env["ir.model.fields"].create(
            {
                "name": "x_user_names",
                "model_id": self.env.ref("base.model_res_groups").id,
                "state": "manual",
                "field_description": "A computed field that depends on users",
                "compute": "for r in self: r['x_user_names'] = ', '.join(r.users.mapped('name'))",
                "depends": "users",
                "store": True,
                "ttype": "char",
            }
        )

        grp_additional = self.env["res.groups"].create({"name": "additional"})
        grp_test.write({'implied_ids': [Command.link(grp_additional.id)]})

        self.assertIn(grp_additional.name, test_user.x_group_names)
        self.assertIn(test_user.name, grp_additional.x_user_names)

    def test_demote_user(self):
        """When a user is demoted to the status of portal/public,
           we should strip him of all his (previous) rights
        """
        group_0 = self.env.ref(self.group0)  # the group to which test_user already belongs
        group_U = self.env["res.groups"].create({"name": "U", "implied_ids": [Command.set([self.grp_internal.id])]})
        self.grp_internal.implied_ids = False  # only there to simplify the test by not having to care about its trans_implied_ids

        self.test_user.write({'groups_id': [Command.link(group_U.id)]})
        self.assertEqual(
            self.test_user.groups_id, (group_0 + group_U + self.grp_internal),
            "We should have our 2 groups and the implied user group",
        )

        # Now we demote him. The JS framework sends 3 and 4 commands,
        # which is what we write here, but it should work even with a 5 command or whatever.
        self.test_user.write({'groups_id': [
            Command.unlink(self.grp_internal.id),
            Command.unlink(self.grp_public.id),
            Command.link(self.grp_portal.id),
        ]})

        # if we screw up the removing groups/adding the implied ids, we could end up in two situations:
        # 1. we have a portal user with way too much rights (e.g. 'Contact Creation', which does not imply any other group)
        # 2. because a group may be (transitively) implying group_user, then it would raise an exception
        # so as a compromise we remove all groups when demoting a user
        # (even technical display groups, e.g. TaxB2B, which could be re-added later)
        self.assertEqual(
            self.test_user.groups_id, (self.grp_portal),
            "Here the portal group does not imply any other group, so we should only have this group.",
        )

    def test_implied_groups(self):
        """ We check that the adding of implied ids works correctly for normal users and portal users.
            In the second case, working normally means raising if a group implies to give 'group_user'
            rights to a portal user.
        """
        U = self.env["res.users"]
        G = self.env["res.groups"]
        group_user = self.env.ref('base.group_user')
        group_portal = self.env.ref('base.group_portal')
        group_no_one = self.env.ref('base.group_no_one')

        group_A = G.create({"name": "A"})
        group_AA = G.create({"name": "AA", "implied_ids": [Command.set([group_A.id])]})
        group_B = G.create({"name": "B"})
        group_BB = G.create({"name": "BB", "implied_ids": [Command.set([group_B.id])]})

        # user_a is a normal user, so we expect groups to be added when we add them,
        # as well as 'implied_groups'; otherwise nothing else should happen.
        # By contrast, for a portal user we want implied groups not to be added
        # if and only if it would not give group_user (or group_public) privileges
        user_a = U.create({"name": "a", "login": "a", "groups_id": [Command.set([group_AA.id, group_user.id])]})
        self.assertEqual(user_a.groups_id, (group_AA + group_A + group_user + group_no_one))

        user_b = U.create({"name": "b", "login": "b", "groups_id": [Command.set([group_portal.id, group_AA.id])]})
        self.assertEqual(user_b.groups_id, (group_AA + group_A + group_portal))

        # user_b is not an internal user, but giving it a new group just added a new group
        (user_a + user_b).write({"groups_id": [Command.link(group_BB.id)]})
        self.assertEqual(user_a.groups_id, (group_AA + group_A + group_BB + group_B + group_user + group_no_one))
        self.assertEqual(user_b.groups_id, (group_AA + group_A + group_BB + group_B + group_portal))

        # now we create a group that implies the group_user
        # adding it to a user should work normally, whereas adding it to a portal user should raise
        group_C = G.create({"name": "C", "implied_ids": [Command.set([group_user.id])]})

        user_a.write({"groups_id": [Command.link(group_C.id)]})
        self.assertEqual(user_a.groups_id, (group_AA + group_A + group_BB + group_B + group_C + group_user + group_no_one))

        with self.assertRaises(ValidationError):
            user_b.write({"groups_id": [Command.link(group_C.id)]})

    def test_has_group_cleared_cache_on_write(self):
        self.registry._clear_cache()
        self.assertFalse(self.registry._Registry__cache, "Ensure ormcache is empty")

        def populate_cache():
            self.test_user.has_group('test_user_has_group.group0')
            self.assertTrue(self.registry._Registry__cache, "user.has_group cache must be populated")

        populate_cache()

        self.env.ref(self.group0).write({"share": True})
        self.assertFalse(self.registry._Registry__cache, "Writing on group must invalidate user.has_group cache")

        populate_cache()
        # call_cache_clearing_methods is called in res.groups.write to invalidate
        # cache before calling its parent class method (`odoo.models.Model.write`)
        # as explain in the `res.group.write` comment.
        # This verifies that calling `call_cache_clearing_methods()` invalidates
        # the ormcache of method `user.has_group()`
        self.env['ir.model.access'].call_cache_clearing_methods()
        self.assertFalse(
            self.registry._Registry__cache,
            "call_cache_clearing_methods() must invalidate user.has_group cache"
        )
