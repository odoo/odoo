# Copyright 2014 ABF OSIELL <http://osiell.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import datetime

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestUserRole(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        cls.user_model = cls.env["res.users"]
        cls.role_model = cls.env["res.users.role"]
        cls.wiz_model = cls.env["wizard.groups.into.role"]

        cls.company1 = cls.env.ref("base.main_company")
        cls.company2 = cls.env["res.company"].create({"name": "company2"})
        cls.default_user = cls.env.ref("base.default_user")
        cls.user_id = cls.user_model.create(
            {"name": "USER TEST (ROLES)", "login": "user_test_roles"}
        )

        # ROLE_1
        cls.group_user_id = cls.env.ref("base.group_user")
        cls.group_no_one_id = cls.env.ref("base.group_no_one")
        vals = {
            "name": "ROLE_1",
            "implied_ids": [(6, 0, [cls.group_user_id.id, cls.group_no_one_id.id])],
        }
        cls.role1_id = cls.role_model.create(vals)

        # ROLE_2
        # Must have group_user in order to have sufficient groups. Check:
        # github.com/odoo/odoo/commit/c3717f3018ce0571aa41f70da4262cc946d883b4
        cls.group_multi_currency_id = cls.env.ref("base.group_multi_currency")
        cls.group_settings_id = cls.env.ref("base.group_system")
        vals = {
            "name": "ROLE_2",
            "implied_ids": [
                (
                    6,
                    0,
                    [
                        cls.group_user_id.id,
                        cls.group_multi_currency_id.id,
                        cls.group_settings_id.id,
                    ],
                )
            ],
        }
        cls.role2_id = cls.role_model.create(vals)

        # Setup for multi-company testing
        cls.multicompany_user_1 = cls.user_model.create(
            {
                "name": "User 2",
                "company_id": cls.company1.id,
                "company_ids": [(6, 0, [cls.company1.id, cls.company2.id])],
                "groups_id": [(6, 0, cls.env.ref("base.group_erp_manager").ids)],
                "login": "multicompany_user_1",
            }
        )
        cls.multicompany_user_2 = cls.user_model.create(
            {
                "name": "User 2",
                "company_id": cls.company2.id,
                "company_ids": [(6, 0, [cls.company2.id])],
                "groups_id": [(6, 0, cls.env.ref("base.group_user").ids)],
                "login": "multicompany_user_2",
            }
        )
        cls.multicompany_role = cls.role_model.create(
            {
                "name": "MULTICOMPANY_ROLE",
                "implied_ids": [(6, 0, [cls.group_user_id.id])],
                "line_ids": [(0, 0, {"user_id": cls.multicompany_user_2.id})],
            }
        )

    def test_role_1(self):
        self.user_id.write({"role_line_ids": [(0, 0, {"role_id": self.role1_id.id})]})
        user_group_ids = sorted({group.id for group in self.user_id.groups_id})
        role_group_ids = self.role1_id.trans_implied_ids.ids
        role_group_ids.append(self.role1_id.group_id.id)
        role_group_ids = sorted(set(role_group_ids))
        self.assertEqual(user_group_ids, role_group_ids)

    def test_role_2(self):
        self.user_id.write({"role_line_ids": [(0, 0, {"role_id": self.role2_id.id})]})
        user_group_ids = sorted({group.id for group in self.user_id.groups_id})
        role_group_ids = self.role2_id.trans_implied_ids.ids
        role_group_ids.append(self.role2_id.group_id.id)
        role_group_ids = sorted(set(role_group_ids))
        self.assertEqual(user_group_ids, role_group_ids)

    def test_role_1_2(self):
        self.user_id.write(
            {
                "role_line_ids": [
                    (0, 0, {"role_id": self.role1_id.id}),
                    (0, 0, {"role_id": self.role2_id.id}),
                ]
            }
        )
        user_group_ids = sorted({group.id for group in self.user_id.groups_id})
        role1_group_ids = self.role1_id.trans_implied_ids.ids
        role1_group_ids.append(self.role1_id.group_id.id)
        role2_group_ids = self.role2_id.trans_implied_ids.ids
        role2_group_ids.append(self.role2_id.group_id.id)
        role_group_ids = sorted(set(role1_group_ids + role2_group_ids))
        self.assertEqual(user_group_ids, role_group_ids)

    def test_role_1_2_with_dates(self):
        today_str = fields.Date.today()
        today = fields.Date.from_string(today_str)
        yesterday = today - datetime.timedelta(days=1)
        yesterday_str = fields.Date.to_string(yesterday)
        self.user_id.write(
            {
                "role_line_ids": [
                    # Role 1 should be enabled
                    (0, 0, {"role_id": self.role1_id.id, "date_from": today_str}),
                    # Role 2 should be disabled
                    (0, 0, {"role_id": self.role2_id.id, "date_to": yesterday_str}),
                ]
            }
        )
        user_group_ids = sorted({group.id for group in self.user_id.groups_id})
        role1_group_ids = self.role1_id.trans_implied_ids.ids
        role1_group_ids.append(self.role1_id.group_id.id)
        role_group_ids = sorted(set(role1_group_ids))
        self.assertEqual(user_group_ids, role_group_ids)

    def test_role_unlink(self):
        # Get role1 groups
        role1_group_ids = (
            self.role1_id.implied_ids.ids + self.role1_id.trans_implied_ids.ids
        )
        role1_group_ids.append(self.role1_id.group_id.id)
        role1_group_ids = sorted(set(role1_group_ids))

        # Configure the user with role1 and role2
        self.user_id.write(
            {
                "role_line_ids": [
                    (0, 0, {"role_id": self.role1_id.id}),
                    (0, 0, {"role_id": self.role2_id.id}),
                ]
            }
        )
        # Remove role2
        self.role2_id.unlink()
        user_group_ids = sorted({group.id for group in self.user_id.groups_id})
        self.assertEqual(user_group_ids, role1_group_ids)
        # Remove role1
        self.role1_id.unlink()
        user_group_ids = sorted({group.id for group in self.user_id.groups_id})
        self.assertEqual(user_group_ids, [])

    def test_role_line_unlink(self):
        # Get role1 groups
        role1_group_ids = (
            self.role1_id.implied_ids.ids + self.role1_id.trans_implied_ids.ids
        )
        role1_group_ids.append(self.role1_id.group_id.id)
        role1_group_ids = sorted(set(role1_group_ids))

        # Configure the user with role1 and role2
        self.user_id.write(
            {
                "role_line_ids": [
                    (0, 0, {"role_id": self.role1_id.id}),
                    (0, 0, {"role_id": self.role2_id.id}),
                ]
            }
        )
        # Remove role2 from the user
        self.user_id.role_line_ids.filtered(
            lambda l: l.role_id.id == self.role2_id.id
        ).unlink()
        user_group_ids = sorted({group.id for group in self.user_id.groups_id})
        self.assertEqual(user_group_ids, role1_group_ids)
        # Remove role1 from the user
        self.user_id.role_line_ids.filtered(
            lambda l: l.role_id.id == self.role1_id.id
        ).unlink()
        user_group_ids = sorted({group.id for group in self.user_id.groups_id})
        self.assertEqual(user_group_ids, [])

    def test_default_user_roles(self):
        self.default_user.write(
            {
                "role_line_ids": [
                    (0, 0, {"role_id": self.role1_id.id}),
                    (0, 0, {"role_id": self.role2_id.id}),
                ]
            }
        )
        user = self.user_model.create(
            {"name": "USER TEST (DEFAULT ROLES)", "login": "user_test_default_roles"}
        )
        roles = self.role_model.browse([self.role1_id.id, self.role2_id.id])
        self.assertEqual(user.role_ids, roles)

    def test_role_multicompany(self):
        """Test AccessError when admin-like user accesses a role"""
        role = self.multicompany_role.with_user(self.multicompany_user_1)
        # Dummy read to check that multicompany user 1 has read access
        role.read()
        # Dummy read to check that multicompany user 1 has read access on the
        # whole role, even if it's using a different company than multicompany
        # user 2 (which is included in the role)
        role.with_context(allowed_company_ids=self.company1.ids).read()
        # Downgrade multicompany user 1 to common user
        self.multicompany_user_1.write(
            {"groups_id": [(6, 0, self.env.ref("base.group_user").ids)]}
        )
        # Check that the user cannot read multicompany data again since it lost
        # its admin privileges
        with self.assertRaisesRegex(
            AccessError, "You are not allowed to access 'User role'"
        ):
            role.read()

    def test_create_role_from_user(self):
        # Use a wizard instance to create a new role based on the user.
        # We use assign_to_user = False, as otherwise this module forcibly
        # assigns the role's groups to the user, which would make this
        # test useless.
        wizard = self.env["wizard.create.role.from.user"].create(
            {
                "name": "Role for user (without assign)",
                "assign_to_user": False,
            }
        )
        result = wizard.with_context(active_ids=[self.user_id.id]).create_from_user()

        # Check that the role has the same groups as the user
        role_id = result["res_id"]
        role = self.role_model.browse([role_id])
        user_group_ids = sorted(set(self.user_id.groups_id.ids))
        role_group_ids = sorted(set(role.trans_implied_ids.ids))
        self.assertEqual(user_group_ids, role_group_ids)

    def test_show_alert_computation(self):
        """Test the computation of the `show_alert` field."""
        self.user_id.write({"role_line_ids": [(0, 0, {"role_id": self.role1_id.id})]})
        self.assertTrue(self.user_id.show_alert)

        # disable role
        self.user_id.role_line_ids.unlink()
        self.assertFalse(self.user_id.show_alert)

    def test_group_groups_into_role(self):
        user_group_ids = [group.id for group in self.user_id.groups_id]
        # Check that there is not a role with name: Test Role
        self.assertFalse(self.role_model.search([("name", "=", "Test Role")]))
        # Call create_role function to group groups into a role
        wizard = self.wiz_model.with_context(active_ids=user_group_ids).create(
            {"name": "Test Role"}
        )
        wizard.create_role()
        # Check that a role with name: Test Role has been created
        new_role = self.role_model.search([("name", "=", "Test Role")])
        self.assertTrue(new_role)
        # Check that the role has the correct groups
        self.assertEqual(set(new_role.implied_ids.ids), set(user_group_ids))
