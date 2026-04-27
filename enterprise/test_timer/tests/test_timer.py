# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError

from odoo.tests.common import TransactionCase


class TestTimer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestTimer, cls).setUpClass()

        # Setup mixin
        cls.test_timer = cls.env['timer.test'].create({'name': 'Timer 1'})
        cls.test_timer_bis = cls.env['timer.test'].create({'name': 'Timer 2'})

        # Setup users
        cls.usr1 = cls.env['res.users'].create({
            'name': 'Usr1',
            'login': 'Usr1',
            'email': 'usr1@test.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

        cls.usr2 = cls.env['res.users'].create({
            'name': 'Usr2',
            'login': 'Usr2',
            'email': 'usr2@test.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })


    def test_timer_from_self_user(self):

        # Start and stop
        self.test_timer.action_timer_start()
        self.assertEqual(len(self.test_timer.user_timer_id), 1, 'It should have created one timer')

        self.test_timer.action_timer_stop()
        self.assertEqual(len(self.test_timer.user_timer_id), 0, 'It should have delete the timer')

        # Start the first timer then the second one
        self.test_timer.action_timer_start()
        self.test_timer_bis.action_timer_start()

        self.assertEqual(len(self.env['timer.timer'].search([])), 2, 'It should have created 2 timers for the same user')
        self.assertFalse(self.test_timer.is_timer_running, "The first timer should be in pause because the second one interrupt it")
        self.assertTrue(self.test_timer_bis.is_timer_running, 'The second timer should be running')

        # Resume the first one
        self.test_timer.action_timer_resume()

        self.assertTrue(self.test_timer.is_timer_running, 'The first timer should be running after being resumed')
        self.assertFalse(self.test_timer_bis.is_timer_running, 'The second timer should be in pause when another timer has been started')

        # Start a new test timer with interruption override
        override_test_timer = self.env['interruption.timer.test'].create({})
        override_test_timer.action_timer_start()

        self.assertEqual(len(self.env['timer.timer'].search([])), 3, 'A third timer should be created')
        self.assertFalse(self.test_timer.is_timer_running, 'The first timer has been interrupted and should be in pause')
        self.assertFalse(self.test_timer_bis.is_timer_running, 'The second timer has been interrupted and should be in pause')
        self.assertTrue(override_test_timer.is_timer_running, 'The third timer should be running')

        # Resume another timer to interrupt the new one
        self.test_timer_bis.action_timer_resume()

        self.assertEqual(len(self.env['timer.timer'].search([])), 2, 'It should remains only 2 timers')
        self.assertEqual(len(override_test_timer.user_timer_id), 0, 'The third timer should be deleted because of his override method')

    def test_timer_with_many_users(self):

        # 2 users, 1 record = 2 timers
        self.test_timer.with_user(self.usr1).action_timer_start()
        self.test_timer.with_user(self.usr2).action_timer_start()

        self.assertEqual(len(self.env['timer.timer'].search([])), 2, 'It should have created two timers')
        self.assertEqual(len(self.test_timer.with_user(self.usr1).user_timer_id), 1, 'It should exist only one timer for this user, model and record')
        self.assertEqual(len(self.test_timer.with_user(self.usr2).user_timer_id), 1, 'It should exist only one timer for this user, model and record')

        # Stop one of them
        self.test_timer.with_user(self.usr2).action_timer_stop()

        self.assertEqual(len(self.env['timer.timer'].search([])), 1, 'It should have deleted one timer')
        self.assertEqual(len(self.test_timer.with_user(self.usr1).user_timer_id), 1, 'It should exist only one timer for this user, model and record')
        self.assertEqual(len(self.test_timer.with_user(self.usr2).user_timer_id), 0, 'It shouldn\'t exit one timer for this user, model and record')

    def test_timer_rounding(self):

        minutes_spent, minimum, rounding = 4.5,10,5
        result = self.test_timer._timer_rounding(minutes_spent, minimum, rounding)
        self.assertEqual(result, 10, 'It should have been round to the minimum amount')

        minutes_spent = 12.4
        result = self.test_timer._timer_rounding(minutes_spent, minimum, rounding)
        self.assertEqual(result, 15, 'It should have been round to the next multiple of 15')

    def test_timer_access_security(self):

        # Create usr1's timer1
        timer1 = self.env['timer.timer'].with_user(self.usr1).create({
            'timer_start' : False,
            'timer_pause' : False,
            'is_timer_running' : False,
            'res_model' : self.test_timer._name,
            'res_id' : self.test_timer.id,
            'user_id' : self.usr1.id,
        })

        # Create usr1's timer2
        timer2 = self.env['timer.timer'].with_user(self.usr1).create({
            'timer_start' : False,
            'timer_pause' : False,
            'is_timer_running' : False,
            'res_model' : self.test_timer_bis._name,
            'res_id' : self.test_timer_bis.id,
            'user_id' : self.usr1.id,
        })

        # Start timer2
        timer2.action_timer_start()

        with self.assertRaises(AccessError):

            # Try to create a timer with usr1 for usr2 (Create)
            self.env['timer.timer'].with_user(self.usr1).create({
                'timer_start' : False,
                'timer_pause' : False,
                'is_timer_running' : False,
                'res_model' : self.test_timer._name,
                'res_id' : self.test_timer.id,
                'user_id' : self.usr2.id,
            })

            # Try to start the timer1 with another usr2 (Write)
            timer1.with_user(self.usr2).action_timer_start()

            # Try to stop the timer2 with usr2 (Unlink)
            timer2.with_user(self.usr2).action_timer_stop()

    def test_timer_unlink_with_other_user(self):
        """
            To ensure that user2's timer is unlinked by user1.
            Follow these steps:
                - User2 starts a timer with User2.
                - verifies that the timer has started.
                - User1 unlinks the timer from their account.
                - verifies that the timer is successfully unlinked and no longer associated with their account.
        """
        self.test_timer_bis.with_user(self.usr2).action_timer_start()
        timer_domain = [('res_id', '=', self.test_timer_bis.id), ('res_model', '=', self.test_timer_bis._name)]
        self.assertEqual(self.env['timer.timer'].search_count(timer_domain), 1, 'It should have created the timer.')
        self.assertEqual(len(self.test_timer_bis.with_user(self.usr2).user_timer_id), 1,
            'It should exist only one timer for this user, model and record')
        self.test_timer_bis.with_user(self.usr1).unlink()
        self.assertEqual(self.env['timer.timer'].search_count(timer_domain), 0, 'It should have deleted the timer.')
