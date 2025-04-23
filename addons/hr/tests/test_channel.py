# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.fields import Command

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestChannel(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super(TestChannel, cls).setUpClass()

        cls.channel = cls.env['discuss.channel'].create({'name': 'Test'})
        cls.user1 = mail_new_test_user(
            cls.env,
            login="user1",
            groups="base.group_user,hr.group_hr_user",
            name="User 1",
            email="user1@example.com",
        )

        emp0 = cls.env['hr.employee'].create({
            'user_id': cls.res_users_hr_officer.id,
        })
        cls.department = cls.env['hr.department'].create({
            'name': 'Test Department',
            'member_ids': [(4, emp0.id)],
        })

    def test_auto_subscribe_department(self):
        self.assertEqual(self.channel.channel_partner_ids, self.env['res.partner'])

        self.channel.write({
            'subscription_department_ids': [(4, self.department.id)]
        })

        self.assertEqual(self.channel.channel_partner_ids, self.department.mapped('member_ids.user_id.partner_id'))

    def test_auto_subscribe_child_department_when_adding_parent(self):
        self.assertEqual(self.channel.channel_partner_ids, self.env["res.partner"])
        emp1 = self.env["hr.employee"].create({"user_id": self.user1.id})
        self.env["hr.department"].create(
            {
                "parent_id": self.department.id,
                "name": "Child Department",
                "member_ids": [Command.link(emp1.id)],
            }
        )

        self.channel.write({"subscription_department_ids": [Command.link(self.department.id)]})

        self.assertEqual(
            self.channel.channel_partner_ids,
            self.department.mapped("member_ids.user_id.partner_id") | emp1.user_id.partner_id,
        )

    def test_auto_subscribe_multi_level_child_department_when_adding_parent(self):
        self.assertEqual(self.channel.channel_partner_ids, self.env["res.partner"])
        emp1 = self.env["hr.employee"].create({"user_id": self.user1.id})
        child_level_1 = self.env["hr.department"].create(
            {
                "parent_id": self.department.id,
                "name": "Child Department",
            }
        )
        self.env["hr.department"].create(
            {
                "parent_id": child_level_1.id,
                "name": "Child Department Level 2",
                "member_ids": [Command.link(emp1.id)],
            }
        )

        self.channel.write({"subscription_department_ids": [Command.link(self.department.id)]})

        self.assertEqual(
            self.channel.channel_partner_ids,
            self.department.mapped("member_ids.user_id.partner_id") | emp1.user_id.partner_id,
        )

    def test_auto_subscribe_child_department_when_creating_employee(self):
        self.assertEqual(self.channel.channel_partner_ids, self.env["res.partner"])
        child_department = self.env["hr.department"].create(
            {
                "parent_id": self.department.id,
                "name": "Child Department",
            }
        )

        self.channel.write({"subscription_department_ids": [Command.link(self.department.id)]})
        emp1 = self.env["hr.employee"].create(
            {
                "user_id": self.user1.id,
                "department_id": child_department.id,
            }
        )

        self.assertEqual(
            self.channel.channel_partner_ids,
            self.department.mapped("member_ids.user_id.partner_id") | emp1.user_id.partner_id,
        )

    def test_auto_subscribe_department_when_changing_parent(self):
        self.assertEqual(self.channel.channel_partner_ids, self.env["res.partner"])
        previous_department = self.env["hr.department"].create(
            {
                "name": "Previous Department",
            }
        )
        child_department = self.env["hr.department"].create(
            {
                "parent_id": previous_department.id,
                "name": "Child Department",
            }
        )
        self.channel.write({"subscription_department_ids": [Command.link(self.department.id)]})
        emp1 = self.env["hr.employee"].create(
            {
                "user_id": self.user1.id,
                "department_id": child_department.id,
            }
        )
        self.assertEqual(
            self.channel.channel_partner_ids,
            self.department.mapped("member_ids.user_id.partner_id"),
        )
        child_department.parent_id = self.department.id
        self.assertEqual(
            self.channel.channel_partner_ids,
            self.department.mapped("member_ids.user_id.partner_id") | emp1.user_id.partner_id,
        )

    def test_auto_subscribe_department_when_changing_employee_department(self):
        emp1 = self.env["hr.employee"].create({"user_id": self.user1.id})
        child_department = self.env["hr.department"].create(
            {
                "parent_id": self.department.id,
                "name": "Child Department",
            }
        )
        self.channel.write({"subscription_department_ids": [Command.link(self.department.id)]})
        self.assertNotIn(self.user1.partner_id, self.channel.channel_partner_ids)

        emp1.department_id = child_department

        self.assertIn(self.user1.partner_id, self.channel.channel_partner_ids)

    def test_auto_subscribe_skips_employee_in_archived_child_department(self):
        archived_department = self.env["hr.department"].create(
            {
                "parent_id": self.department.id,
                "name": "Archived Child Department",
                "member_ids": [Command.link(self.env["hr.employee"].create({"user_id": self.user1.id}).id)],
            }
        )
        archived_department.action_archive()

        self.channel.write({"subscription_department_ids": [Command.link(self.department.id)]})

        self.assertEqual(
            self.channel.channel_partner_ids,
            self.department.member_ids.user_id.partner_id,
        )

    def test_remove_department_parent_logs_no_warning(self):
        child_department = self.env["hr.department"].create(
            {
                "parent_id": self.department.id,
                "name": "Child Department",
            }
        )
        with self.assertNoLogs("odoo", "WARNING"):
            child_department.parent_id = False
