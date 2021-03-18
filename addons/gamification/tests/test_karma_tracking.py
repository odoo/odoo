# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo import exceptions, fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common


class TestKarmaTrackingCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestKarmaTrackingCommon, cls).setUpClass()
        cls.test_user = mail_new_test_user(
            cls.env, login='test',
            name='Test User', email='test@example.com',
            karma=0,
            groups='base.group_user',
        )
        cls.test_user_2 = mail_new_test_user(
            cls.env, login='test2',
            name='Test User 2', email='test2@example.com',
            karma=0,
            groups='base.group_user',
        )
        cls.env['gamification.karma.tracking'].search([]).unlink()

        cls.test_date = fields.Date.today() + relativedelta(month=4, day=1)

    @classmethod
    def _create_trackings(cls, user, karma, steps, track_date, days_delta=1):
        old_value = user.karma
        for step in range(steps):
            new_value = old_value + karma
            cls.env['gamification.karma.tracking'].create([{
                'user_id': user.id,
                'old_value': old_value,
                'new_value': new_value,
                'consolidated': False,
                'tracking_date': fields.Date.to_string(track_date)
            }])
            old_value = new_value
            track_date = track_date + relativedelta(days=days_delta)

    def test_computation_gain(self):
        self._create_trackings(self.test_user, 20, 2, self.test_date, days_delta=30)
        self._create_trackings(self.test_user_2, 10, 20, self.test_date, days_delta=2)

        results = (self.test_user | self.test_user_2)._get_tracking_karma_gain_position([])
        self.assertEqual(results[0]['user_id'], self.test_user_2.id)
        self.assertEqual(results[0]['karma_gain_total'], 200)
        self.assertEqual(results[0]['karma_position'], 1)
        self.assertEqual(results[1]['user_id'], self.test_user.id)
        self.assertEqual(results[1]['karma_gain_total'], 40)
        self.assertEqual(results[1]['karma_position'], 2)

        results = (self.test_user | self.test_user_2)._get_tracking_karma_gain_position([], to_date=self.test_date + relativedelta(day=2))
        self.assertEqual(results[0]['user_id'], self.test_user.id)
        self.assertEqual(results[0]['karma_gain_total'], 20)
        self.assertEqual(results[0]['karma_position'], 1)
        self.assertEqual(results[1]['user_id'], self.test_user_2.id)
        self.assertEqual(results[1]['karma_gain_total'], 10)
        self.assertEqual(results[1]['karma_position'], 2)

        results = (self.test_user | self.test_user_2)._get_tracking_karma_gain_position([], from_date=self.test_date + relativedelta(months=1, day=1))
        self.assertEqual(results[0]['user_id'], self.test_user_2.id)
        self.assertEqual(results[0]['karma_gain_total'], 50)
        self.assertEqual(results[0]['karma_position'], 1)
        self.assertEqual(results[1]['user_id'], self.test_user.id)
        self.assertEqual(results[1]['karma_gain_total'], 20)
        self.assertEqual(results[1]['karma_position'], 2)

        results = self.env['res.users']._get_tracking_karma_gain_position([])
        self.assertEqual(len(results), 0)

    def test_consolidation_cron(self):
        self.patcher = patch('odoo.addons.gamification.models.gamification_karma_tracking.fields.Date', wraps=fields.Date)
        self.mock_datetime = self.patcher.start()
        self.mock_datetime.today.return_value = date(self.test_date.year, self.test_date.month + 1, self.test_date.day)

        self._create_trackings(self.test_user, 20, 2, self.test_date, days_delta=30)
        self._create_trackings(self.test_user_2, 10, 20, self.test_date, days_delta=2)
        self.env['gamification.karma.tracking']._consolidate_last_month()
        consolidated = self.env['gamification.karma.tracking'].search([
            ('user_id', 'in', (self.test_user | self.test_user_2).ids),
            ('consolidated', '=', True),
            ('tracking_date', '=', self.test_date)
        ])
        self.assertEqual(len(consolidated), 2)
        unconsolidated = self.env['gamification.karma.tracking'].search([
            ('user_id', 'in', (self.test_user | self.test_user_2).ids),
            ('consolidated', '=', False),
        ])
        self.assertEqual(len(unconsolidated), 6)  # 5 for test user 2, 1 for test user

        self.patcher.stop()

    def test_consolidation_monthly(self):
        Tracking = self.env['gamification.karma.tracking']
        base_test_user_karma = self.test_user.karma
        base_test_user_2_karma = self.test_user_2.karma
        self._create_trackings(self.test_user, 20, 2, self.test_date, days_delta=30)
        self._create_trackings(self.test_user_2, 10, 20, self.test_date, days_delta=2)

        Tracking._process_consolidate(self.test_date)
        consolidated = Tracking.search([
            ('user_id', '=', self.test_user_2.id),
            ('consolidated', '=', True),
            ('tracking_date', '=', self.test_date)
        ])
        self.assertEqual(len(consolidated), 1)
        self.assertEqual(consolidated.old_value, base_test_user_2_karma)  # 15 2-days span, from 1 to 29 included = 15 steps -> 150 karma
        self.assertEqual(consolidated.new_value, base_test_user_2_karma + 150)  # 15 2-days span, from 1 to 29 included = 15 steps -> 150 karma

        remaining = Tracking.search([
            ('user_id', '=', self.test_user_2.id),
            ('consolidated', '=', False)
        ])
        self.assertEqual(len(remaining), 5)  # 15 steps consolidated, remaining 5
        self.assertEqual(remaining[0].tracking_date, self.test_date + relativedelta(months=1, day=9))  # ordering: last first
        self.assertEqual(remaining[-1].tracking_date, self.test_date + relativedelta(months=1, day=1))

        Tracking._process_consolidate(self.test_date + relativedelta(months=1))
        consolidated = Tracking.search([
            ('user_id', '=', self.test_user_2.id),
            ('consolidated', '=', True),
        ])
        self.assertEqual(len(consolidated), 2)
        self.assertEqual(consolidated[0].new_value, base_test_user_2_karma + 200)  # 5 remaining 2-days span, from 1 to 9 included = 5 steps -> 50 karma
        self.assertEqual(consolidated[0].old_value, base_test_user_2_karma + 150)  # coming from previous iteration
        self.assertEqual(consolidated[0].tracking_date, self.test_date + relativedelta(months=1))  # tracking set at beginning of month
        self.assertEqual(consolidated[-1].new_value, base_test_user_2_karma + 150)  # previously created one still present
        self.assertEqual(consolidated[-1].old_value, base_test_user_2_karma)  # previously created one still present

        remaining = Tracking.search([
            ('user_id', '=', self.test_user_2.id),
            ('consolidated', '=', False)
        ])
        self.assertFalse(remaining)

        # current user not-in-details tests
        current_user_trackings = Tracking.search([
            ('user_id', '=', self.test_user.id),
        ])
        self.assertEqual(len(current_user_trackings), 2)
        self.assertEqual(current_user_trackings[0].new_value, base_test_user_karma + 40)
        self.assertEqual(current_user_trackings[-1].old_value, base_test_user_karma)

    def test_user_as_erp_manager(self):
        self.test_user.write({'groups_id': [
            (4, self.env.ref('base.group_partner_manager').id),
            (4, self.env.ref('base.group_erp_manager').id)
        ]})
        user = self.env['res.users'].with_user(self.test_user).create({
            'name': 'Test Ostérone', 'karma': '32',
            'login': 'dummy', 'email': 'dummy@example.com',
        })
        with self.assertRaises(exceptions.AccessError):
            user.read(['karma_tracking_ids'])

        user.write({'karma': 60})
        user.add_karma(10)
        self.assertEqual(user.karma, 70)
        trackings = self.env['gamification.karma.tracking'].sudo().search([('user_id', '=', user.id)])
        self.assertEqual(len(trackings), 3)  # create + write + add_karma

    def test_user_tracking(self):
        self.test_user.write({'groups_id': [
            (4, self.env.ref('base.group_partner_manager').id),
            (4, self.env.ref('base.group_system').id)
        ]})
        user = self.env['res.users'].with_user(self.test_user).create({
            'name': 'Test Ostérone', 'karma': '32',
            'login': 'dummy', 'email': 'dummy@example.com',
        })
        self.assertEqual(user.karma, 32)
        self.assertEqual(len(user.karma_tracking_ids), 1)
        self.assertEqual(user.karma_tracking_ids.old_value, 0)
        self.assertEqual(user.karma_tracking_ids.new_value, 32)

        user.write({'karma': 60})
        user.add_karma(10)
        self.assertEqual(user.karma, 70)
        self.assertEqual(len(user.karma_tracking_ids), 3)
        self.assertEqual(user.karma_tracking_ids[2].old_value, 60)
        self.assertEqual(user.karma_tracking_ids[2].new_value, 70)
        self.assertEqual(user.karma_tracking_ids[1].old_value, 32)
        self.assertEqual(user.karma_tracking_ids[1].new_value, 60)
        self.assertEqual(user.karma_tracking_ids[0].old_value, 0)
        self.assertEqual(user.karma_tracking_ids[0].new_value, 32)


class TestComputeRankCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestComputeRankCommon, cls).setUpClass()

        def _patched_send_mail(*args, **kwargs):
            pass

        patch_email = patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail', _patched_send_mail)
        patch_email.start()

        cls.users = cls.env['res.users']
        for k in range(-5, 1030, 30):
            cls.users += mail_new_test_user(
                cls.env,
                name=str(k),
                login="test_recompute_rank_%s" % k,
                karma=k,
            )

        cls.env['gamification.karma.rank'].search([]).unlink()

        cls.rank_1 = cls.env['gamification.karma.rank'].create({
            'name': 'rank 1',
            'karma_min': 1,
        })

        cls.rank_2 = cls.env['gamification.karma.rank'].create({
            'name': 'rank 2',
            'karma_min': 250,
        })

        cls.rank_3 = cls.env['gamification.karma.rank'].create({
            'name': 'rank 3',
            'karma_min': 500,
        })
        cls.rank_4 = cls.env['gamification.karma.rank'].create({
            'name': 'rank 4',
            'karma_min': 1000,
        })

        patch_email.stop()

    def test_00_initial_compute(self):

        self.assertEqual(len(self.users), 35)

        self.assertEqual(
            len(self.rank_1.user_ids & self.users),
            len([u for u in self.users if u.karma >= self.rank_1.karma_min and u.karma < self.rank_2.karma_min])
        )
        self.assertEqual(
            len(self.rank_2.user_ids & self.users),
            len([u for u in self.users if u.karma >= self.rank_2.karma_min and u.karma < self.rank_3.karma_min])
        )
        self.assertEqual(
            len(self.rank_3.user_ids & self.users),
            len([u for u in self.users if u.karma >= self.rank_3.karma_min and u.karma < self.rank_4.karma_min])
        )
        self.assertEqual(
            len(self.rank_4.user_ids & self.users),
            len([u for u in self.users if u.karma >= self.rank_4.karma_min])
        )

    def test_01_switch_rank(self):

        self.assertEqual(len(self.users), 35)

        self.rank_3.karma_min = 100
        # rank_1 -> rank_3 -> rank_2 -> rank_4

        self.assertEqual(
            len(self.rank_1.user_ids & self.users),
            len([u for u in self.users if u.karma >= self.rank_1.karma_min and u.karma < self.rank_3.karma_min])
        )
        self.assertEqual(
            len(self.rank_3.user_ids & self.users),
            len([u for u in self.users if u.karma >= self.rank_3.karma_min and u.karma < self.rank_2.karma_min])
        )
        self.assertEqual(
            len(self.rank_2.user_ids & self.users),
            len([u for u in self.users if u.karma >= self.rank_2.karma_min and u.karma < self.rank_4.karma_min])
        )
        self.assertEqual(
            len(self.rank_4.user_ids & self.users),
            len([u for u in self.users if u.karma >= self.rank_4.karma_min])
        )

    def test_02_update_rank_without_switch(self):
        number_of_users = False

        def _patched_recompute_rank(_self, *args, **kwargs):
            nonlocal number_of_users
            number_of_users = len(_self & self.users)

        patch_bulk = patch('odoo.addons.gamification.models.res_users.Users._recompute_rank', _patched_recompute_rank)
        patch_bulk.start()
        self.rank_3.karma_min = 700
        self.assertEqual(number_of_users, 7, "Should just recompute for the 7 users between 500 and 700")
        patch_bulk.stop()

    def test_03_test_bulk_call(self):
        self.assertEqual(len(self.users), 35)

        def _patched_check_in_bulk(*args, **kwargs):
            raise

        patch_bulk = patch('odoo.addons.gamification.models.res_users.Users._recompute_rank_bulk', _patched_check_in_bulk)
        patch_bulk.start()

        # call on 5 users should not trigger the bulk function
        self.users[0:5]._recompute_rank()

        # call on 50 users should trigger the bulk function
        with self.assertRaises(Exception):
            self.users[0:50]._recompute_rank()

        patch_bulk.stop()
