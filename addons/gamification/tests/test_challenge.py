# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class test_challenge(common.TransactionCase):

    def test_00_join_challenge(self):
        employees_group = self.env.ref('base.group_user')
        user_ids = employees_group.users
        challenge = self.env.ref('gamification.challenge_base_discover')

        self.assertGreaterEqual(len(challenge.user_ids), len(user_ids), "Not enough users in base challenge")

        self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'R2D2',
            'login': 'r2d2@openerp.com',
            'email': 'r2d2@openerp.com',
            'groups_id': [(6, 0, [employees_group.id])]
        })

        challenge._update_all()
        self.assertGreaterEqual(len(challenge.user_ids), len(user_ids)+1, "These are not droids you are looking for")

    def test_10_reach_challenge(self):
        Goals = self.env['gamification.goal']
        challenge = self.env.ref('gamification.challenge_base_discover')

        challenge.state = 'inprogress'
        self.assertEqual(challenge.state, 'inprogress', "Challenge failed the change of state")

        goal_ids = Goals.search([('challenge_id', '=', challenge.id), ('state', '!=', 'draft')])
        self.assertEqual(len(goal_ids), len(challenge.line_ids) * len(challenge.user_ids.ids), "Incorrect number of goals generated, should be 1 goal per user, per challenge line")

        demo = self.env.ref('base.user_demo')
        # demo user will set a timezone
        demo.tz = "Europe/Brussels"
        goal_ids = Goals.search([('user_id', '=', demo.id), ('definition_id', '=', self.env.ref('gamification.definition_base_timezone').id)])

        goal_ids.update_goal()

        missed = goal_ids.filtered(lambda g: g.state != 'reached')
        self.assertFalse(missed, "Not every goal was reached after changing timezone")

        # reward for two firsts as admin may have timezone
        badge_id = self.env.ref('gamification.badge_good_job').id
        challenge.write({'reward_first_id': badge_id, 'reward_second_id': badge_id})
        challenge.state = 'done'

        badge_ids = self.env['gamification.badge.user'].search([('badge_id', '=', badge_id), ('user_id', '=', demo.id)])
        self.assertEqual(len(badge_ids), 1, "Demo user has not received the badge")
