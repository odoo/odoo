# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestChannel(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super(TestChannel, cls).setUpClass()

        cls.channel = cls.env['discuss.channel'].create({'name': 'Test'})

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
        self.assertEqual(self.channel.channel_partner_ids, self.env['res.partner'])
        user1 = mail_new_test_user(self.env, login='user1', groups='base.group_user,hr.group_hr_user', name='User 1', email='user1@example.com')
        emp1 = self.env['hr.employee'].create({
            'user_id': user1.id,
        })
        self.department.create({
            'parent_id': self.department.id,
            "name": "Child Department",
            'member_ids': [(4, emp1.id)],
        })

        self.channel.write({
            'subscription_department_ids': [(4, self.department.id)]
        })

        self.assertEqual(self.channel.channel_partner_ids, self.department.mapped('member_ids.user_id.partner_id') | emp1.user_id.partner_id)

    def test_auto_subscribe_multi_level_child_department_when_adding_parent(self):
        self.assertEqual(self.channel.channel_partner_ids, self.env['res.partner'])
        user1 = mail_new_test_user(self.env, login='user1', groups='base.group_user,hr.group_hr_user', name='User 1', email='user1@example.com')
        emp1 = self.env['hr.employee'].create({
            'user_id': user1.id,
        })
        child_level_1 = self.department.create({
            'parent_id': self.department.id,
            "name": "Child Department",
        })
        self.department.create({
            'parent_id': child_level_1.id,
            "name": "Child Department Level 2",
            'member_ids': [(4, emp1.id)],
        })

        self.channel.write({
            'subscription_department_ids': [(4, self.department.id)]
        })

        self.assertEqual(self.channel.channel_partner_ids, self.department.mapped('member_ids.user_id.partner_id') | emp1.user_id.partner_id)

    def test_auto_subscribe_child_department_when_creating_employee(self):
        self.assertEqual(self.channel.channel_partner_ids, self.env['res.partner'])
        user1 = mail_new_test_user(self.env, login='user1', groups='base.group_user,hr.group_hr_user', name='User 1', email='user1@example.com')
        child_department = self.department.create({
            'parent_id': self.department.id,
            "name": "Child Department",
        })

        self.channel.write({
            'subscription_department_ids': [(4, self.department.id)]
        })
        emp1 = self.env['hr.employee'].create({
            'user_id': user1.id,
            'department_id': child_department.id,
        })

        self.assertEqual(self.channel.channel_partner_ids, self.department.mapped('member_ids.user_id.partner_id') | emp1.user_id.partner_id)
