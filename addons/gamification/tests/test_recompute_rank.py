# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from unittest.mock import patch


class TestComputeRankCommon(common.TransactionCase):

    def setUp(self):
        super(TestComputeRankCommon, self).setUp()

        def _patched_send_mail(*args, **kwargs):
            pass

        self.User = self.env['res.users'].with_context(no_reset_password=True, mail_create_nosubscribe=True)
        self.users = self.User

        patch_email = patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail', _patched_send_mail)
        patch_email.start()
        for k in range(-5, 1030, 30):
            self.users += self.User.create({
                'name': str(k),
                'login': "test_recompute_rank_%s" % k,
                'karma': k,
            })

        self.env['gamification.karma.rank'].search([]).unlink()

        self.rank_1 = self.env['gamification.karma.rank'].create({
            'name': 'rank 1',
            'karma_min': 0,
        })

        self.rank_2 = self.env['gamification.karma.rank'].create({
            'name': 'rank 2',
            'karma_min': 250,
        })

        self.rank_3 = self.env['gamification.karma.rank'].create({
            'name': 'rank 3',
            'karma_min': 500,
        })
        self.rank_4 = self.env['gamification.karma.rank'].create({
            'name': 'rank 4',
            'karma_min': 1000,
        })

        patch_email.stop()


class test_recompute(TestComputeRankCommon):

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
