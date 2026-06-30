from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import tagged
from odoo.addons.hr.tests.common import TestHrCommon


@tagged('post_install', '-at_install')
class TestGamificationBadge(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super(TestHrCommon, cls).setUpClass()
        cls.demo_user, cls.demo2_user, cls.demo3_user, cls.demo4_manager = (cls.env["res.users"].with_context(no_reset_password=True)
        .create([
            {
                "name": "demo_user",
                "login": "demo@odoo.com",
                "email": "demo@odoo.com",
                "group_ids": [Command.link(cls.env.ref("base.group_user").id)],
            }, {
                "name": "demo2_user",
                "login": "demo2@odoo.com",
                "email": "demo2@odoo.com",
                "group_ids": [Command.link(cls.env.ref("base.group_user").id)],
            }, {
                "name": "demo3_user",
                "login": "demo3@odoo.com",
                "email": "demo3@odoo.com",
                "group_ids": [Command.link(cls.env.ref("base.group_user").id)],
            }, {
                "name": "demo4_manager",
                "login": "demo4@odoo.com",
                "email": "demo4@odoo.com",
                "group_ids": [Command.link(cls.env.ref("hr.group_hr_user").id)],
            },
        ]))
        cls.demo_user.action_create_employee()

        cls.env["gamification.badge.user.wizard"].with_user(cls.demo2_user).create([{
            "badge_id": cls.env.ref("gamification.badge_good_job").id,
            "comment": f"{cls.demo_user.name} is a good developer",
            "user_id": cls.demo_user.id,
        }]).action_grant_badge()

    def test_update_badge(self):
        """
            Test for who can update the bade.
            case 1: The one who has given the badge should be able to update the badge
            case 2: The one who has group Officer: Manage all employees access should be able to edit any badge
            case 3: The one who has not given the badge(base user) should not be able to update the badge
        """
        badge_user = self.env["gamification.badge.user"].search([], limit=1)[0]
        user_comment = "This person is a good guy"

        badge_user.with_user(self.demo2_user).write({'comment': user_comment})
        self.assertEqual(user_comment, badge_user.comment)

        badge_user.with_user(self.demo4_manager).write({'comment': user_comment + 'manager'})
        self.assertEqual(user_comment + 'manager', badge_user.comment)

        with self.assertRaises(AccessError):
            badge_user.with_user(self.demo3_user).write({'comment': user_comment})

    def test_delete_badge(self):
        """
            Test for who can delete the bade.
            case 1: The one who has not given the badge(base user) should not be able to delete the badge
            case 2: The one who has given the badge should be able to delete the badge
            case 3: The one who has group Officer: Manage all employees access should be able to edit any badge
        """
        badge_user = self.env["gamification.badge.user"].search([], limit=1)[0]
        with self.assertRaises(AccessError):
            badge_user.with_user(self.demo3_user).unlink()

        badge_user.with_user(self.demo2_user.id).unlink()
        self.assertEqual(0, self.env['gamification.badge.user'].search_count([('id', '=', badge_user.id)], limit=1))

        self.env["gamification.badge.user.wizard"].with_user(self.demo2_user).create([{
            "badge_id": self.env.ref("gamification.badge_good_job").id,
            "comment": f"{self.demo_user.name} is a good developer",
            "user_id": self.demo_user.id,
        }]).action_grant_badge()

        badge_user = self.env["gamification.badge.user"].search([], limit=1)[0]
        badge_user.with_user(self.demo4_manager.id).unlink()
        self.assertEqual(0, self.env['gamification.badge.user'].search_count([('id', '=', badge_user.id)], limit=1))
