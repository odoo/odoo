from odoo.addons.hr.tests.common import TestHrCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tests import Form


@tagged('post_install', '-at_install')
class TestGamificationBadgeWizard(TestHrCommon):
    @classmethod
    def setUpClass(self):
        super(TestHrCommon, self).setUpClass()
        # creating demo users
        self.demo_user, self.demo2_user, self.demo3_user = (self.env["res.users"].with_context(no_reset_password=True)
        .create([
            {
                "name": "demo_user",
                "login": "demo@odoo.com",
                "email": "demo@odoo.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }, {
                "name": "demo2_user",
                "login": "demo2@odoo.com",
                "email": "demo2@odoo.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }, {
                "name": "demo3_user",
                "login": "demo3@odoo.com",
                "email": "demo3@odoo.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        ]))
        self.demo_user.action_create_employee()

        # demo2_user giving badge to demo_user
        self.env["gamification.badge.user.wizard"].with_user(self.demo2_user.id).create({
            "badge_id": self.env.ref("gamification.badge_good_job").id,
            "comment": f"{self.demo_user.name} is a good developer",
            "user_id": self.demo_user.id,
        }).action_grant_badge()

    def test_update_badge_wizard(self):
        """
            Test for who can update the bade.
            case 1: The one who has given the badge should be able to update the badge
            case 2: The one who has not given the badge(base user) should not be able to update the badge
        """
        badge_user = self.env["gamification.badge.user"].search([], limit=1)[0]
        new_comment = "This person is a good guy"
        # case1
        with Form(
            self.env["gamification.current.badge.wizard"].with_context(
                badge_user.action_open_badge().get("context")
            )
        ) as form:
            form.comment = new_comment
        form.save().with_user(self.demo2_user.id).action_update_current_badge()

        # updated text should be the same
        self.assertEqual(new_comment, self.env["gamification.badge.user"].browse(badge_user.id).comment)

        # case2
        with self.assertRaises(UserError):
            with Form(
                self.env["gamification.current.badge.wizard"].with_context(
                    badge_user.action_open_badge().get("context")
                )
            ) as form:
                pass
            form.save().with_user(self.demo3_user.id).action_update_current_badge()

    def test_delete_badge_wizard(self):
        """
            Test for who can delete the bade.
            case 1: The one who has given the badge should be able to delete the badge
            case 2: The one who has not given the badge(base user) should not be able to delete the badge
        """
        badge_user = self.env["gamification.badge.user"].search([], limit=1)[0]
        # case2
        with self.assertRaises(UserError):
            with Form(
                self.env["gamification.current.badge.wizard"].with_context(
                    badge_user.action_open_badge().get("context")
                )
            ) as form:
                pass
            form.save().with_user(self.demo3_user.id).action_delete_current_badge()

        # case1
        with Form(
            self.env["gamification.current.badge.wizard"].with_context(
                badge_user.action_open_badge().get("context")
            )
        ) as form:
            pass
        form.save().with_user(self.demo2_user.id).action_delete_current_badge()
        self.assertEqual(0, self.env['gamification.badge.user'].search_count([('id', '=', badge_user.id)], limit=1))
