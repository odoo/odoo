# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests import common
from odoo.tests import tagged


@tagged('moderation')
class TestMessageModeration(common.Moderation):

    @classmethod
    def setUpClass(cls):
        super(TestMessageModeration, cls).setUpClass()

    def test_is_moderator(self):
        self.assertTrue(self.user_employee.is_moderator)
        self.assertFalse(self.user_admin.is_moderator)
        self.assertTrue(self.user_employee_2.is_moderator)

    def test_moderation_counter(self):
        self._create_new_message(self.channel_1.id, status='pending_moderation', author=self.partner_admin)
        self._create_new_message(self.channel_1.id, status='accepted', author=self.partner_admin)
        self._create_new_message(self.channel_1.id, status='accepted', author=self.partner_employee)
        self._create_new_message(self.channel_1.id, status='pending_moderation', author=self.partner_employee)
        self._create_new_message(self.channel_1.id, status='accepted', author=self.partner_employee_2)

        self.assertEqual(self.user_employee.moderation_counter, 2)
        self.assertEqual(self.user_employee_2.moderation_counter, 0)
        self.assertEqual(self.user_admin.moderation_counter, 0)

        self.channel_1.write({'channel_partner_ids': [(4, self.partner_employee_2.id)], 'moderator_ids': [(4, self.user_employee_2.id)]})
        self.assertEqual(self.user_employee.moderation_counter, 2)
        self.assertEqual(self.user_employee_2.moderation_counter, 0)
        self.assertEqual(self.user_admin.moderation_counter, 0)
