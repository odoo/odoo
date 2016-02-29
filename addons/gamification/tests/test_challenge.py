# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class test_challenge(common.TransactionCase):

    def setUp(self):
        super(test_challenge, self).setUp()

        self.User = self.env['res.users']
        self.Line = self.env['gamification.challenge.line']
        self.Goal = self.env['gamification.goal']
        self.BadgeUser = self.env['gamification.badge.user']

        self.demo_user = self.env.ref('base.user_demo')
        self.group_user = self.env.ref('base.group_user')
        self.challenge_base = self.env.ref('gamification.challenge_base_discover')
        self.definition_timezone = self.env.ref('gamification.definition_base_timezone')
        self.badge = self.env.ref('gamification.badge_good_job')

    def test_00_join_challenge(self):

        user_count = self.User.search_count([('groups_id', '=', self.group_user.id)])

        self.assertGreaterEqual(len(self.challenge_base.user_ids), user_count, "Not enough users in base challenge")

        self.User.with_context(no_reset_password=True).create({
            'name': 'R2D2',
            'login': 'r2d2@openerp.com',
            'email': 'r2d2@openerp.com',
            'groups_id': [(6, 0, [self.group_user.id])]
        })

        self.challenge_base._update_all()
        self.assertGreaterEqual(len(self.challenge_base.user_ids), user_count+1, "These are not droids you are looking for")

    def test_10_reach_challenge(self):

        self.challenge_base.write({'state': 'inprogress'})

        self.assertEqual(self.challenge_base.state, 'inprogress', "Challenge failed the change of state")

        line_count = self.Line.search_count([('challenge_id', '=', self.challenge_base.id)])
        goal_count = self.Goal.search_count([('challenge_id', '=', self.challenge_base.id), ('state', '!=', 'draft')])
        self.assertEqual(goal_count, line_count*len(self.challenge_base.user_ids), "Incorrect number of goals generated, should be 1 goal per user, per challenge line")

        # demo user will set a timezone
        self.demo_user.write({'tz': "Europe/Brussels"})
        goals = self.Goal.search([('user_id', '=', self.demo_user.id), ('definition_id', '=', self.definition_timezone.id)])
        
        goals.update_goal()
        reached_goals = self.Goal.search([('id', 'in', goals.ids), ('state', '=', 'reached')])
        self.assertEqual(set(goals.ids), set(reached_goals.ids), "Not every goal was reached after changing timezone")

        # reward for two firsts as admin may have timezone
        self.challenge_base.write({'reward_first_id': self.badge.id, 'reward_second_id': self.badge.id, 'state': 'done'})

        badge_user_count = self.BadgeUser.search_count([('badge_id', '=', self.badge.id), ('user_id', '=', self.demo_user.id)])
        self.assertGreater(badge_user_count, 0, "Demo user has not received the badge")
