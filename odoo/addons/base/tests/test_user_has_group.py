from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestHasGroup(TransactionCase):
    def setUp(self):
        super().setUp()

        self.group0 = "test_user_has_group.group0"
        self.group1 = "test_user_has_group.group1"
        group0, _group1 = self.env["res.groups"]._load_records(
            [
                {"xml_id": self.group0, "values": {"name": "group0"}},
                {"xml_id": self.group1, "values": {"name": "group1"}},
            ]
        )

        self.test_user = self.env["res.users"].create(
            {
                "login": "testuser",
                "partner_id": self.env["res.partner"]
                .create({"name": "Strawman Test User"})
                .id,
                "group_ids": [Command.set([group0.id])],
            }
        )

        self.grp_internal_xml_id = "base.group_user"
        self.grp_internal = self.env.ref(self.grp_internal_xml_id)
        self.grp_portal_xml_id = "base.group_portal"
        self.grp_portal = self.env.ref(self.grp_portal_xml_id)
        self.grp_public_xml_id = "base.group_public"
        self.grp_public = self.env.ref(self.grp_public_xml_id)

    def test_env_uid(self):
        Partner = self.env["res.partner"].with_user(self.test_user)
        self.assertTrue(
            Partner.env.user.has_group(self.group0),
            "the test user should belong to group0",
        )
        self.assertFalse(
            Partner.env.user.has_group(self.group1),
            "the test user should *not* belong to group1",
        )

    def test_record(self):
        self.assertTrue(
            self.test_user.has_group(self.group0),
            "the test user should belong to group0",
        )
        self.assertFalse(
            self.test_user.has_group(self.group1),
            "the test user shoudl not belong to group1",
        )

    def test_other_user(self):
        internal_user = self.test_user.copy({"group_ids": self.grp_internal})
        internal_user = internal_user.with_user(internal_user)
        test_user = (
            self.env["res.users"].with_user(self.test_user).browse(self.test_user.id)
        )

        test_user.has_group(self.group0)
        with self.assertRaises(AccessError):
            test_user.browse(internal_user.id).has_group(self.group0)
        test_user.sudo().browse(internal_user.id).has_group(self.group0)

        internal_user.has_group(self.group0)
        internal_user.browse(test_user.id).has_group(self.group0)

    def test_portal_creation(self):
        grp_test_portal_xml_id = "test_user_has_group.portal_implied_group"
        grp_test_portal = self.env["res.groups"]._load_records(
            [
                {
                    "xml_id": grp_test_portal_xml_id,
                    "values": {"name": "Test Group Portal"},
                }
            ]
        )
        grp_test_internal1 = self.env["res.groups"]._load_records(
            [
                {
                    "xml_id": "test_user_has_group.internal_implied_group1",
                    "values": {"name": "Test Group Itnernal 1"},
                }
            ]
        )
        grp_test_internal2_xml_id = "test_user_has_group.internal_implied_group2"
        grp_test_internal2 = self.env["res.groups"]._load_records(
            [
                {
                    "xml_id": grp_test_internal2_xml_id,
                    "values": {"name": "Test Group Internal 2"},
                }
            ]
        )

        self.grp_portal.implied_ids = grp_test_portal

        grp_test_internal1.implied_ids = False
        grp_test_internal2.implied_ids = False

        portal_user = self.env["res.users"].create(
            {
                "login": "portalTest",
                "name": "Portal test",
                "group_ids": [self.grp_portal.id, grp_test_internal2.id],
            }
        )

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
            "The portal user should belong to '%s'" % grp_test_internal2_xml_id,
        )
        self.assertFalse(
            portal_user.has_group(self.grp_internal_xml_id),
            "The portal user should not belong to '%s'" % self.grp_internal_xml_id,
        )

        portal_user.unlink()

        grp_test_internal1.implied_ids = self.grp_internal
        grp_test_internal2.implied_ids = self.grp_internal

        with self.assertRaises(ValidationError):
            portal_user = self.env["res.users"].create(
                {
                    "login": "portalFail",
                    "name": "Portal fail",
                    "group_ids": [self.grp_portal.id, grp_test_internal2.id],
                }
            )

    def test_portal_write(self):
        grp_test_portal = self.env["res.groups"].create({"name": "implied by portal"})
        self.grp_portal.implied_ids = grp_test_portal

        portal_user = self.env["res.users"].create(
            {
                "login": "portalTest2",
                "name": "Portal test 2",
                "group_ids": [Command.set([self.grp_portal.id])],
            }
        )

        self.assertEqual(portal_user.group_ids, self.grp_portal)
        self.assertEqual(
            portal_user.all_group_ids,
            (self.grp_portal + grp_test_portal),
            "The portal user should have the implied group.",
        )

        grp_fail = self.env["res.groups"].create(
            {
                "name": "fail",
                "implied_ids": [Command.set([self.grp_internal.id])],
            }
        )

        with self.assertRaises(ValidationError):
            portal_user.write({"group_ids": [Command.link(grp_fail.id)]})

    def test_two_user_types(self):
        grp_test = self.env["res.groups"]._load_records(
            [
                {
                    "xml_id": "test_two_user_types.implied_groups",
                    "values": {"name": "Test Group"},
                }
            ]
        )
        grp_test.implied_ids += self.grp_internal
        grp_test.implied_ids += self.grp_portal

        with self.assertRaises(ValidationError):
            self.env["res.users"].create(
                {
                    "login": "test_two_user_types",
                    "name": "Test User with two user types",
                    "group_ids": [Command.set([grp_test.id])],
                }
            )

        test_user = self.env["res.users"].create(
            {
                "login": "test_user_portal",
                "name": "Test User with two user types",
                "group_ids": [Command.set([self.grp_portal.id])],
            }
        )
        with self.assertRaises(ValidationError):
            self.grp_internal.user_ids = [Command.link(test_user.id)]

    def test_two_user_types_implied_groups(self):
        grp_test = self.env["res.groups"].create(
            {
                "name": "test",
                "implied_ids": [Command.set([self.grp_internal.id])],
            }
        )

        test_user = self.env["res.users"].create(
            {
                "login": "test_user_portal",
                "name": "Test User with one user types",
                "group_ids": [Command.set([grp_test.id])],
            }
        )

        with self.assertRaises(
            ValidationError, msg="Test user belongs to two user types."
        ):
            grp_test.write({"implied_ids": [Command.link(self.grp_portal.id)]})

        self.env["ir.model.fields"].create(
            {
                "name": "x_group_names",
                "model_id": self.env.ref("base.model_res_users").id,
                "state": "manual",
                "field_description": "A computed field that depends on all_group_ids",
                "compute": "for r in self: r['x_group_names'] = ', '.join(r.all_group_ids.mapped('name'))",
                "depends": "all_group_ids",
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
                "compute": "for r in self: r['x_user_names'] = ', '.join(r.all_user_ids.mapped('name'))",
                "depends": "all_user_ids",
                "store": True,
                "ttype": "char",
            }
        )

        grp_additional = self.env["res.groups"].create({"name": "additional"})
        grp_test.write({"implied_ids": [Command.link(grp_additional.id)]})

        self.assertIn(grp_additional.name, test_user.x_group_names)
        self.assertIn(test_user.name, grp_additional.x_user_names)

    def test_demote_user(self):
        group_0 = self.env.ref(self.group0)
        group_U = self.env["res.groups"].create(
            {"name": "U", "implied_ids": [Command.set([self.grp_internal.id])]}
        )

        self.grp_internal.implied_ids = False

        self.assertEqual(self.test_user.group_ids, group_0)
        self.assertEqual(self.test_user.all_group_ids, group_0)

        self.test_user.write({"group_ids": [Command.link(group_U.id)]})

        self.assertEqual(
            self.test_user.group_ids,
            (group_0 + group_U),
            "We should have our 2 groups",
        )
        self.assertEqual(
            self.test_user.all_group_ids,
            (group_0 + group_U + self.grp_internal),
            "We should have our 2 groups and the implied user group",
        )

        with self.assertRaises(ValidationError):
            self.test_user.write(
                {
                    "group_ids": [
                        Command.unlink(self.grp_internal.id),
                        Command.unlink(self.grp_public.id),
                        Command.link(self.grp_portal.id),
                    ]
                }
            )

        self.test_user.write(
            {
                "group_ids": [
                    Command.unlink(group_U.id),
                    Command.unlink(self.grp_public.id),
                    Command.link(self.grp_portal.id),
                ]
            }
        )

        self.assertEqual(
            self.test_user.all_group_ids,
            (group_0 | self.grp_portal.all_implied_ids),
            "Only the portal group and whatever the installed modules make it imply should remain.",
        )

    def test_implied_groups(self):
        U = self.env["res.users"]
        G = self.env["res.groups"]
        group_user = self.env.ref("base.group_user")
        group_portal = self.env.ref("base.group_portal")
        implied_by_user = group_user.all_implied_ids
        implied_by_portal = group_portal.all_implied_ids

        group_A = G.create({"name": "A"})
        group_AA = G.create({"name": "AA", "implied_ids": [Command.set([group_A.id])]})
        group_B = G.create({"name": "B"})
        group_BB = G.create({"name": "BB", "implied_ids": [Command.set([group_B.id])]})

        user_a = U.create(
            {
                "name": "a",
                "login": "a",
                "group_ids": [Command.set([group_AA.id, group_user.id])],
            }
        )
        self.assertEqual(
            user_a.all_group_ids,
            (group_AA + group_A + implied_by_user),
        )
        self.assertEqual(user_a.group_ids, (group_AA + group_user))

        user_b = U.create(
            {
                "name": "b",
                "login": "b",
                "group_ids": [Command.set([group_portal.id, group_AA.id])],
            }
        )
        self.assertEqual(user_b.all_group_ids, (group_AA + group_A + implied_by_portal))
        self.assertEqual(user_b.group_ids, (group_AA + group_portal))

        (user_a + user_b).write({"group_ids": [Command.link(group_BB.id)]})
        self.assertEqual(
            user_a.all_group_ids,
            (group_AA + group_A + group_BB + group_B + implied_by_user),
        )
        self.assertEqual(
            user_b.all_group_ids,
            (group_AA + group_A + group_BB + group_B + implied_by_portal),
        )
        self.assertEqual(user_a.group_ids, (group_AA + group_BB + group_user))
        self.assertEqual(user_b.group_ids, (group_AA + group_BB + group_portal))

        group_C = G.create({"name": "C", "implied_ids": [Command.set([group_user.id])]})

        user_a.write({"group_ids": [Command.link(group_C.id)]})
        self.assertEqual(
            user_a.all_group_ids,
            (group_AA + group_A + group_BB + group_B + group_C + implied_by_user),
        )
        self.assertEqual(user_a.group_ids, (group_AA + group_BB + group_C + group_user))

        with self.assertRaises(ValidationError):
            user_b.write({"group_ids": [Command.link(group_C.id)]})

    def test_has_group_cleared_cache_on_write(self):
        self.env.registry.clear_cache()
        self.assertFalse(
            self.registry.ormcache_lrus["default"],
            "Ensure ormcache is empty",
        )

        def populate_cache():
            self.test_user.has_group("test_user_has_group.group0")
            self.assertTrue(
                self.registry.ormcache_lrus["default"],
                "user._has_group cache must be populated",
            )

        populate_cache()

        self.env.ref(self.group0).write({"share": True})
        self.assertFalse(
            self.registry.ormcache_lrus["default"],
            "Writing on group must invalidate user._has_group cache",
        )

        populate_cache()
        self.env["ir.access"]._clear_access_caches()
        self.assertFalse(
            self.registry.ormcache_lrus["default"],
            "_clear_access_caches() must invalidate user._has_group cache",
        )

    def test_has_group_with_new_id(self):
        user = self.env["res.users"].new({"partner_id": self.test_user.partner_id.id})
        self.assertEqual(user.has_group(self.group0), False)
        self.assertEqual(user.has_group(self.group1), False)

        user2 = self.env["res.users"].new(
            {"partner_id": self.test_user.partner_id.id}, origin=self.test_user
        )
        self.assertEqual(user2.has_group(self.group0), True)
        self.assertEqual(user2.has_group(self.group1), False)
