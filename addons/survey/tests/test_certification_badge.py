# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.tests import common
from psycopg2 import IntegrityError
from odoo.exceptions import AccessError
from odoo.tools import mute_logger


class TestCertificationBadge(common.TestSurveyCommon):

    def setUp(self):
        super(TestCertificationBadge, self).setUp()
        self.certification_survey = self.env['survey.survey'].with_user(self.survey_manager).create({
            'title': 'Certification Survey',
            'access_mode': 'public',
            'users_login_required': True,
            'scoring_type': 'scoring_with_answers',
            'certification': True,
        })

        self.certification_survey_2 = self.env['survey.survey'].with_user(self.survey_manager).create({
            'title': 'Another Certification Survey',
            'access_mode': 'public',
            'users_login_required': True,
            'scoring_type': 'scoring_with_answers',
            'certification': True,
        })

        self.certification_badge = self.env['gamification.badge'].with_user(self.survey_manager).create({
            'name': self.certification_survey.title,
            'description': 'Congratulations, you have succeeded this certification',
            'rule_auth': 'nobody',
            'level': None,
        })

        self.certification_badge_2 = self.env['gamification.badge'].with_user(self.survey_manager).create({
            'name': self.certification_survey.title + ' 2',
            'description': 'Congratulations, you have succeeded this certification',
            'rule_auth': 'nobody',
            'level': None,
        })

        self.certification_badge_3 = self.env['gamification.badge'].with_user(self.survey_manager).create({
            'name': self.certification_survey.title + ' 3',
            'description': 'Congratulations, you have succeeded this certification',
            'rule_auth': 'nobody',
            'level': None,
        })

    def test_archive(self):
        """ Archive status of survey is propagated to its badges. """
        self.certification_survey.write({
            'certification_give_badge': True,
            'certification_badge_id': self.certification_badge.id
        })

        self.certification_survey.action_archive()
        self.assertFalse(self.certification_survey.active)
        self.assertFalse(self.certification_badge.active)

        self.certification_survey.action_unarchive()
        self.assertTrue(self.certification_survey.active)
        self.assertTrue(self.certification_badge.active)

    def test_set_same_badge_on_multiple_survey(self):
        self.certification_survey.write({
            'certification_give_badge': True,
            'certification_badge_id': self.certification_badge.id
        })
        # set the same badge on another survey should fail:
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.certification_survey_2.write({
                    'certification_give_badge': True,
                    'certification_badge_id': self.certification_badge.id
                })
                self.certification_survey.flush()

    def test_badge_configuration(self):
        """ Test badge synchronization """
        # add a certification badge on a new survey
        challenge = self.env['gamification.challenge'].search([('reward_id', '=', self.certification_badge.id)])
        self.assertEqual(len(challenge), 0, """A challenge should not exist or be linked to the certification badge 
            if the certification badge have not been activated on a certification survey""")

        self.certification_survey.write({
            'certification_give_badge': True,
            'certification_badge_id': self.certification_badge.id
        })

        challenge = self.env['gamification.challenge'].search([('reward_id', '=', self.certification_badge.id)])
        self.assertEqual(len(challenge), 1,
            "A challenge should be created if the certification badge is activated on a certification survey")
        challenge_line = self.env['gamification.challenge.line'].search([('challenge_id', '=', challenge.id)])
        self.assertEqual(len(challenge_line), 1,
            "A challenge_line should be created if the certification badge is activated on a certification survey")
        goal = challenge_line.definition_id
        self.assertEqual(len(goal), 1,
            "A goal should be created if the certification badge is activated on a certification survey")

        # don't give badge anymore
        self.certification_survey.write({'certification_give_badge': False})
        self.assertEqual(self.certification_badge.id, self.certification_survey.certification_badge_id.id,
                         'The certification badge should still be set on certification survey even if give_badge is false.')
        self.assertEqual(self.certification_badge.active, False,
                         'The certification badge should be inactive if give_badge is false.')

        challenge = self.env['gamification.challenge'].search([('id', '=', challenge.id)])
        self.assertEqual(len(challenge), 0,
            "The challenge should be deleted if the certification badge is unset from the certification survey")
        challenge_line = self.env['gamification.challenge.line'].search([('id', '=', challenge_line.id)])
        self.assertEqual(len(challenge_line), 0,
            "The challenge_line should be deleted if the certification badge is unset from the certification survey")
        goal = self.env['gamification.goal'].search([('id', '=', goal.id)])
        self.assertEqual(len(goal), 0,
            "The goal should be deleted if the certification badge is unset from the certification survey")

        # re active the badge in the survey
        self.certification_survey.write({'certification_give_badge': True})
        self.assertEqual(self.certification_badge.active, True,
                         'The certification badge should be active if give_badge is true.')

        challenge = self.env['gamification.challenge'].search([('reward_id', '=', self.certification_badge.id)])
        self.assertEqual(len(challenge), 1,
            "A challenge should be created if the certification badge is activated on a certification survey")
        challenge_line = self.env['gamification.challenge.line'].search([('challenge_id', '=', challenge.id)])
        self.assertEqual(len(challenge_line), 1,
            "A challenge_line should be created if the certification badge is activated on a certification survey")
        goal = challenge_line.definition_id
        self.assertEqual(len(goal), 1,
            "A goal should be created if the certification badge is activated on a certification survey")

        # If 'certification_give_badge' is True but no certification badge is linked, ValueError should be raised
        duplicate_survey = self.certification_survey.copy()
        self.assertFalse(duplicate_survey.certification_give_badge, "Value for field 'certification_give_badge' should not be copied")
        self.assertEqual(duplicate_survey.certification_badge_id, self.env['gamification.badge'], "Badge should be empty")
        with self.assertRaises(ValueError):
            duplicate_survey.write({'certification_give_badge': True})

    def test_certification_badge_access(self):
        self.certification_badge.with_user(self.survey_manager).write(
            {'description': "Spoiler alert: I'm Aegon Targaryen and I sleep with the Dragon Queen, who is my aunt by the way! So I can do whatever I want! Even if I know nothing!"})
        self.certification_badge.with_user(self.survey_user).write({'description': "Youpie Yeay!"})
        with self.assertRaises(AccessError):
            self.certification_badge.with_user(self.user_emp).write({'description': "I'm a dude who think that has every right on the Iron Throne"})
        with self.assertRaises(AccessError):
            self.certification_badge.with_user(self.user_portal).write({'description': "Guy, you just can't do that !"})
        with self.assertRaises(AccessError):
            self.certification_badge.with_user(self.user_public).write({'description': "What did you expect ? Schwepps !"})

    def test_badge_configuration_multi(self):
        vals = {
            'title': 'Certification Survey',
            'access_mode': 'public',
            'users_login_required': True,
            'scoring_type': 'scoring_with_answers',
            'certification': True,
            'certification_give_badge': True,
            'certification_badge_id': self.certification_badge.id,
        }
        survey_1 = self.env['survey.survey'].create(vals.copy())
        vals.update({'certification_badge_id': self.certification_badge_2.id})
        survey_2 = self.env['survey.survey'].create(vals.copy())
        vals.update({'certification_badge_id': self.certification_badge_3.id})
        survey_3 = self.env['survey.survey'].create(vals)

        certification_surveys = self.env['survey.survey'].browse([survey_1.id, survey_2.id, survey_3.id])
        self.assertEqual(len(certification_surveys), 3, 'There should be 3 certification survey created')

        challenges = self.env['gamification.challenge'].search([('reward_id', 'in', certification_surveys.mapped('certification_badge_id').ids)])
        self.assertEqual(len(challenges), 3, "3 challenges should be created")
        challenge_lines = self.env['gamification.challenge.line'].search([('challenge_id', 'in', challenges.ids)])
        self.assertEqual(len(challenge_lines), 3, "3 challenge_lines should be created")
        goals = challenge_lines.mapped('definition_id')
        self.assertEqual(len(goals), 3, "3 goals should be created")

        # Test write multi
        certification_surveys.write({'certification_give_badge': False})
        for survey in certification_surveys:
            self.assertEqual(survey.certification_badge_id.active, False,
                             'Every badge should be inactive if the 3 survey does not give badge anymore')

        challenges = self.env['gamification.challenge'].search([('id', 'in', challenges.ids)])
        self.assertEqual(len(challenges), 0, "The 3 challenges should be deleted")
        challenge_lines = self.env['gamification.challenge.line'].search([('id', 'in', challenge_lines.ids)])
        self.assertEqual(len(challenge_lines), 0, "The 3 challenge_lines should be deleted")
        goals = self.env['gamification.goal'].search([('id', 'in', goals.ids)])
        self.assertEqual(len(goals), 0, "The 3 goals should be deleted")

        certification_surveys.write({'certification_give_badge': True})
        for survey in certification_surveys:
            self.assertEqual(survey.certification_badge_id.active, True,
                             'Every badge should be reactivated if the 3 survey give badges again')

        challenges = self.env['gamification.challenge'].search([('reward_id', 'in', certification_surveys.mapped('certification_badge_id').ids)])
        self.assertEqual(len(challenges), 3, "3 challenges should be created")
        challenge_lines = self.env['gamification.challenge.line'].search([('challenge_id', 'in', challenges.ids)])
        self.assertEqual(len(challenge_lines), 3, "3 challenge_lines should be created")
        goals = challenge_lines.mapped('definition_id')
        self.assertEqual(len(goals), 3, "3 goals should be created")
