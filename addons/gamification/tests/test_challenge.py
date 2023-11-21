# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo.addons.gamification.tests.common import TransactionCaseGamification
from odoo.exceptions import UserError
from odoo.tools import mute_logger


class TestGamificationCommon(TransactionCaseGamification):

    def setUp(self):
        super(TestGamificationCommon, self).setUp()
        employees_group = self.env.ref('base.group_user')
        self.user_ids = employees_group.users

        # Push demo user into the challenge before creating a new one
        self.env.ref('gamification.challenge_base_discover')._update_all()
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

        demo = self.user_demo
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

    @mute_logger('odoo.models.unlink')
    def test_20_update_all_goals_filter(self):
        # Enroll two internal and two portal users in the challenge
        (
            portal_login_before_update,
            portal_login_after_update,
            internal_login_before_update,
            internal_login_after_update,
        ) = all_test_users = self.env['res.users'].create([
            {
                'name': f'{kind} {age} login',
                'login': f'{kind}_{age}',
                'email': f'{kind}_{age}',
                'groups_id': [(6, 0, groups_id)],
            }
            for kind, groups_id in (
                ('Portal', []),
                ('Internal', [self.env.ref('base.group_user').id]),
            )
            for age in ('Old', 'Recent')
        ])

        challenge = self.env.ref('gamification.challenge_base_discover')
        challenge.write({
            'state': 'inprogress',
            'user_domain': False,
            'user_ids': [(6, 0, all_test_users.ids)]
        })

        # Setup user access logs
        self.env['res.users.log'].search([('create_uid', 'in', challenge.user_ids.ids)]).unlink()
        now = datetime.datetime.now()

        # Create "old" log in records
        self.env['res.users.log'].create([
            {"create_uid": internal_login_before_update.id, 'create_date': now - datetime.timedelta(minutes=3)},
            {"create_uid": portal_login_before_update.id, 'create_date': now - datetime.timedelta(minutes=3)},
        ])

        # Reset goal objective values
        all_test_users.partner_id.tz = False

        # Regenerate all goals
        self.env["gamification.goal"].search([]).unlink()
        self.assertFalse(self.env['gamification.goal'].search([]))

        challenge.action_check()
        goal_ids = self.env['gamification.goal'].search(
            [('challenge_id', '=', challenge.id), ('state', '!=', 'draft'), ('user_id', 'in', challenge.user_ids.ids)]
        )
        self.assertEqual(len(goal_ids), 4)
        self.assertEqual(set(goal_ids.mapped('state')), {'inprogress'})

        # Create more recent log in records
        self.env['res.users.log'].create([
            {"create_uid": internal_login_after_update.id, 'create_date': now + datetime.timedelta(minutes=3)},
            {"create_uid": portal_login_after_update.id, 'create_date': now + datetime.timedelta(minutes=3)},
        ])

        # Update goal objective checked by goal definition
        all_test_users.partner_id.write({'tz': 'Europe/Paris'})

        # Update goals as done by _cron_update
        challenge._update_all()
        unchanged_goal_id = self.env['gamification.goal'].search([
            ('challenge_id', '=', challenge.id),
            ('state', '=', 'inprogress'),  # others were updated to "reached"
            ('user_id', 'in', challenge.user_ids.ids),
        ])
        # Check that even though login record for internal user is older than goal update, their goal was reached.
        self.assertEqual(
            portal_login_before_update,
            unchanged_goal_id.user_id,
            "Only portal user last logged in before last challenge update should not have been updated.",
        )


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
