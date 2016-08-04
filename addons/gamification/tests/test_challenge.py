# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class test_challenge(common.TransactionCase):

    def setUp(self):
        super(test_challenge, self).setUp()

        self.User = self.env['res.users']
        self.ChallengeLine = self.env['gamification.challenge.line']
        self.Goal = self.env['gamification.goal']
        self.BadgeUser = self.env['gamification.badge.user']

        self.demo_user = self.env.ref('base.user_demo')
        self.challenge_base = self.env.ref('gamification.challenge_base_discover')

        self.group_user_id = self.ref('base.group_user')
        self.definition_timezone_id = self.ref('gamification.definition_base_timezone')
        self.badge_id = self.ref('gamification.badge_good_job')

    def test_00_join_challenge(self):
        users_count = self.User.search_count([('groups_id', '=', self.group_user_id)])

        self.assertGreaterEqual(len(self.challenge_base.user_ids), users_count, "Not enough users in base challenge")

        self.User.with_context(no_reset_password=True).create({
            'name': 'R2D2',
            'login': 'r2d2@odoo.com',
            'email': 'r2d2@odoo.com',
            'groups_id': [(6, 0, [self.group_user_id])]
        })

        self.challenge_base._update_all()
        self.assertGreaterEqual(len(self.challenge_base.user_ids), users_count + 1, "These are not droids you are looking for")

    def test_10_reach_challenge(self):
        self.challenge_base.write({'state': 'inprogress'})

        self.assertEqual(self.challenge_base.state, 'inprogress', "Challenge failed the change of state")

        challenge_lines_count = self.ChallengeLine.search_count([('challenge_id', '=', self.challenge_base.id)])
        goals_count = self.Goal.search_count([('challenge_id', '=', self.challenge_base.id), ('state', '!=', 'draft')])
        self.assertEqual(goals_count, challenge_lines_count * len(self.challenge_base.user_ids.ids), "Incorrect number of goals generated, should be 1 goal per user, per challenge line")

        # demo user will set a timezone
        self.demo_user.write({'tz': "Europe/Brussels"})
        goals = self.Goal.search([('user_id', '=', self.demo_user.id), ('definition_id', '=', self.definition_timezone_id)])

        goals.update_goal()
        reached_goals = self.Goal.search([('id', 'in', goals.ids), ('state', '=', 'reached')])
        self.assertEqual(set(goals), set(reached_goals), "Not every goal was reached after changing timezone")

        # reward for two firsts as admin may have timezone
        self.challenge_base.write({'reward_first_id': self.badge_id, 'reward_second_id': self.badge_id})
        self.challenge_base.write({'state': 'done'})

        badges_count = self.BadgeUser.search_count([('badge_id', '=', self.badge_id), ('user_id', '=', self.demo_user.id)])
        self.assertGreater(badges_count, 0, "Demo user has not received the badge")
