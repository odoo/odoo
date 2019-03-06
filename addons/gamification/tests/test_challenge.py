# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import common


class TestGamificationCommon(common.TransactionCase):

    def setUp(self):
        super(TestGamificationCommon, self).setUp()
        employees_group = self.env.ref('base.group_user')
        self.user_ids = employees_group.users

        self.robot = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'R2D2',
            'login': 'r2d2@openerp.com',
            'email': 'r2d2@openerp.com',
            'groups_id': [(6, 0, [employees_group.id])]
        })
        self.badge_good_job = self.env.ref('gamification.badge_good_job')


class test_challenge(TestGamificationCommon):

    def test_00_join_challenge(self):
        challenge = self.env.ref('gamification.challenge_base_discover')

        self.assertGreaterEqual(len(challenge.user_ids), len(self.user_ids), "Not enough users in base challenge")
        challenge._update_all()
        self.assertGreaterEqual(len(challenge.user_ids), len(self.user_ids)+1, "These are not droids you are looking for")

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
        badge_id = self.badge_good_job.id
        challenge.write({'reward_first_id': badge_id, 'reward_second_id': badge_id})
        challenge.state = 'done'

        badge_ids = self.env['gamification.badge.user'].search([('badge_id', '=', badge_id), ('user_id', '=', demo.id)])
        self.assertEqual(len(badge_ids), 1, "Demo user has not received the badge")


class test_badge_wizard(TestGamificationCommon):

    def test_grant_badge(self):
        wiz = self.env['gamification.badge.user.wizard'].create({
            'user_id': self.env.user.id,
            'badge_id': self.badge_good_job.id,
        })
        with self.assertRaises(UserError, msg="A user cannot grant a badge to himself"):
            wiz.action_grant_badge()
        wiz.user_id = self.robot.id
        self.assertTrue(wiz.action_grant_badge(), "Could not grant badge")

        self.assertEqual(self.badge_good_job.stat_this_month, 1)
