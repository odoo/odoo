# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestChannel(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super(TestChannel, cls).setUpClass()

        cls.channel = cls.env['discuss.channel'].create({'name': 'Test'})

        cls.emp0 = cls.env['hr.employee'].create({
            'user_id': cls.res_users_hr_officer.id,
        })
        cls.department = cls.env['hr.department'].create({
            'name': 'Test Department',
        })

    def test_auto_subscribe_department(self):
        self.assertEqual(self.channel.channel_partner_ids, self.env['res.partner'])
        self.emp0.write({'department_id': self.department.id})
        self.department.invalidate_recordset(['member_ids'])
        self.assertEqual(self.department.member_ids, self.emp0)

        self.channel.write({
            'auto_subscribe': True,
            'subscription_department_ids': [(4, self.department.id)]
        })

        self.assertEqual(self.channel.channel_partner_ids, self.emp0.user_id.partner_id)

    def test_auto_subscribe_when_updating_employee_department(self):
        self.channel.write({
            'auto_subscribe': True,
            'subscription_department_ids': [(4, self.department.id)],
        })
        self.assertEqual(self.channel.channel_partner_ids, self.env['res.partner'])
        self.department.invalidate_recordset(['member_ids'])

        self.emp0.write({'department_id': self.department.id})

        self.assertEqual(self.channel.channel_partner_ids, self.emp0.user_id.partner_id)

    def test_auto_subscribe_group_department(self):
        self.department.invalidate_recordset(['member_ids'])
        self.emp0.write({'department_id': self.department.id})
        self.channel.write({
            'auto_subscribe': True,
            'group_ids': [(4, self.env.ref("base.group_system").id)],
            'subscription_department_ids': [(4, self.department.id)],
        })
        both_partners = self.env.ref('base.user_admin').partner_id | self.emp0.user_id.partner_id
        self.assertEqual(self.channel.channel_partner_ids, both_partners)
