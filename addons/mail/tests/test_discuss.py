# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import TestMail
from odoo.tools import mute_logger


class TestDiscuss(TestMail):
    # TDE TODO: tests on the redirection controller

    def test_alias_setup(self):
        alias = self.env['mail.alias'].with_context(alias_model_name='mail.test').create({'alias_name': 'b4r+_#_R3wl$$'})
        self.assertEqual(alias.alias_name, 'b4r+_-_r3wl-', 'Disallowed chars should be replaced by hyphens')

    def test_10_cache_invalidation(self):
        """ Test that creating a mail-thread record does not invalidate the whole cache. """
        # make a new record in cache
        record = self.env['res.partner'].new({'name': 'Brave New Partner'})
        self.assertTrue(record.name)

        # creating a mail-thread record should not invalidate the whole cache
        self.env['res.partner'].create({'name': 'Actual Partner'})
        self.assertTrue(record.name)


    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_needaction(self):
        # needaction use Inbox notification
        (self.user_employee | self.user_admin).write({'notification_type': 'inbox'})

        na_emp1_base = self.test_pigs.sudo(self.user_employee).message_needaction_counter
        na_emp2_base = self.test_pigs.sudo().message_needaction_counter

        self.test_pigs.message_post(body='Test', message_type='comment', subtype='mail.mt_comment', partner_ids=[self.user_employee.partner_id.id])

        na_emp1_new = self.test_pigs.sudo(self.user_employee).message_needaction_counter
        na_emp2_new = self.test_pigs.sudo().message_needaction_counter
        self.assertEqual(na_emp1_new, na_emp1_base + 1)
        self.assertEqual(na_emp2_new, na_emp2_base)

    def test_message_set_star(self):
        msg = self.test_pigs.message_post(body='My Body', subject='1')
        msg_emp = self.env['mail.message'].sudo(self.user_employee).browse(msg.id)

        # Admin set as starred
        msg.toggle_message_starred()
        self.assertTrue(msg.starred)

        # Employee set as starred
        msg_emp.toggle_message_starred()
        self.assertTrue(msg_emp.starred)

        # Do: Admin unstars msg
        msg.toggle_message_starred()
        self.assertFalse(msg.starred)
        self.assertTrue(msg_emp.starred)

    def test_60_cache_invalidation(self):
        msg_cnt = len(self.test_pigs.message_ids)
        self.test_pigs.message_post(body='Hi!', subject='test')
        self.assertEqual(len(self.test_pigs.message_ids), msg_cnt + 1)
