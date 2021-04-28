# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import users

class TestMailCategoryStates(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailCategoryStates, cls).setUpClass()

    @users('employee')
    def test_get_category_states_should_create_new_record_if_not_existing(self):
        states = self.env['mail.category.states'].search([
            ('user_id', '=', self.user_employee.id)
        ], limit=1)
        self.assertFalse(states, "no records should exist")

        self.env['mail.category.states'].get_category_states()
        states =  self.env['mail.category.states'].search([
            ('user_id', '=', self.user_employee.id)
        ], limit=1)
        self.assertTrue(states, "a record should be created after get_category_states is called")

    @users('employee')
    def test_get_category_states_should_return_category_open_states(self):
        self.env['mail.category.states'].create({
            'is_category_channel_open': False,
            'is_category_chat_open': True,
            'user_id': self.user_employee.id,
        })
        states = self.env['mail.category.states'].get_category_states()
        self.assertEqual(
            states['is_category_channel_open'],
            False,
            'info should contain correct channel state'
        )
        self.assertEqual(
            states['is_category_chat_open'],
            True,
            'info should contain correct chat state'
        )

    @users('employee')
    def test_set_category_states_should_create_new_record_if_not_existing(self):
        states = self.env['mail.category.states'].search([
            ('user_id', '=', self.user_employee.id)
        ], limit=1)
        self.assertFalse(states, "no records should exist")

        self.env['mail.category.states'].set_category_states('chat', True)
        states =  self.env['mail.category.states'].search([
            ('user_id', '=', self.user_employee.id)
        ], limit=1)
        self.assertTrue(states, "a record should be created after set_category_states is called")

    @users('employee')
    def test_set_category_states_should_send_notification_on_bus(self):
        self.env['mail.category.states'].create({
            'is_category_channel_open': False,
            'is_category_chat_open': False,
            'user_id': self.user_employee.id,
        })

        with self.assertBus([(self.cr.dbname, 'res.partner', self.partner_employee.id)]):
            self.env['mail.category.states'].set_category_states('chat', True)

    @users('employee')
    def test_set_category_states_should_set_category_state_properly(self):
        self.env['mail.category.states'].create({
            'is_category_channel_open': False,
            'is_category_chat_open': False,
            'user_id': self.user_employee.id,
        })

        states =  self.env['mail.category.states'].search([
            ('user_id', '=', self.user_employee.id)
        ], limit=1)
        self.env['mail.category.states'].set_category_states('chat', True)
        self.assertEqual(
            states.is_category_chat_open,
            True,
            "category state should be updated correctly"
        )
