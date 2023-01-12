# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.onboarding.tests.common import TestOnboardingCommon


class TestOnboarding(TestOnboardingCommon):
    def test_onboarding_completion_global(self):
        # Completing onboarding as company_1
        self.assertEqual(self.env.company, self.company_1)
        self.assertDictEqual(
            self.onboarding_1.current_progress_id._get_and_update_onboarding_state(),
            {self.onboarding_1_step_1.id: 'not_done', self.onboarding_1_step_2.id: 'not_done'})

        self.onboarding_1_step_1.action_set_just_done()
        # Test completed step state consolidation from `just_done` to `done`
        self.assertDictEqual(
            self.onboarding_1.current_progress_id._get_and_update_onboarding_state(),
            {self.onboarding_1_step_1.id: 'just_done', self.onboarding_1_step_2.id: 'not_done'})
        self.assertDictEqual(
            self.onboarding_1.current_progress_id._get_and_update_onboarding_state(),
            {self.onboarding_1_step_1.id: 'done', self.onboarding_1_step_2.id: 'not_done'})
        self.assert_step_is_done(self.onboarding_1_step_1, self.company_2)
        self.assert_onboarding_is_not_done(self.onboarding_1, self.company_2)

        self.onboarding_1_step_2.action_set_just_done()
        self.assert_step_is_done(self.onboarding_1_step_2, self.company_2)
        self.assert_onboarding_is_done(self.onboarding_1, self.company_2)

        # Once onboarding is done, a key 'onboarding_state' is added to the rendering values
        self.assertDictEqual(
            self.onboarding_1.current_progress_id._get_and_update_onboarding_state(),
            {self.onboarding_1_step_1.id: 'done', self.onboarding_1_step_2.id: 'just_done', 'onboarding_state': 'just_done'})
        # Consolidate values
        self.assertDictEqual(
            self.onboarding_1.current_progress_id._get_and_update_onboarding_state(),
            {self.onboarding_1_step_1.id: 'done', self.onboarding_1_step_2.id: 'done', 'onboarding_state': 'done'})

        self.onboarding_1.current_progress_id.action_close()
        self.assertTrue(self.onboarding_1.current_progress_id.is_onboarding_closed)

        # Adding new step resets onboarding state to 'not_done' even if closed
        onboarding_1_step_3 = self.env['onboarding.onboarding.step'].create({
            'title': 'Test Onboarding 1 - Step 3',
            'onboarding_id': self.onboarding_1.id,
            'panel_step_open_action_name': 'action_fake_open_onboarding_step',
        })
        self.assert_step_is_not_done(onboarding_1_step_3)
        self.assert_onboarding_is_not_done(self.onboarding_1)

        # Completing it sets onboarding state to done again
        onboarding_1_step_3.action_set_just_done()
        self.assert_onboarding_is_done(self.onboarding_1)

        # If a company is added, onboarding is 'done'
        company_3 = self.env.company.create({
            'currency_id': self.env.ref('base.EUR').id,
            'name': 'Another Test Company',
        })
        self.assert_onboarding_is_done(self.onboarding_1.with_company(company_3))

        # Adding new step resets onboarding state to 'not_done'
        self.env['onboarding.onboarding.step'].create({
            'title': 'Test Onboarding 1 - Step 4',
            'onboarding_id': self.onboarding_1.id,
            'panel_step_open_action_name': 'action_fake_open_onboarding_step',
        })

        # Closing the panel still allows to track if all steps are completed
        self.onboarding_1.action_close()
        self.assertTrue(self.onboarding_1.current_progress_id.is_onboarding_closed)
        self.assert_onboarding_is_not_done(self.onboarding_1)

    def test_onboarding_completion_per_company(self):
        """Checks the behavior of onboarding and step states in multi-company setting:
        the onboarding state has to track the completion of each of its steps, global and
        per-company, to determine if whether it is completed.
        """
        # Completing onboarding as company_1
        self.assertEqual(self.env.company, self.company_1)

        # Updating onboarding to per-company
        self.onboarding_1.is_per_company = True
        # Required after progress reset (simulate role of controller)
        self.onboarding_1._search_or_create_progress()

        self.onboarding_1_step_1.action_set_just_done()
        self.assert_step_is_done(self.onboarding_1_step_1)

        self.onboarding_1_step_2.action_set_just_done()
        self.assert_onboarding_is_done(self.onboarding_1)

        # Completing onboarding as existing company_2
        self.activate_company(self.company_2)
        # First access from company_2
        self.onboarding_1._search_or_create_progress()

        # Blank state for company 2
        self.assert_step_is_not_done(self.onboarding_1_step_1)
        self.assert_onboarding_is_not_done(self.onboarding_1)

        # But no change for company 1
        self.assert_step_is_done(self.onboarding_1_step_1.with_company(self.company_1))
        self.assert_onboarding_is_done(self.onboarding_1.with_company(self.company_1))

        self.onboarding_1_step_1.action_set_just_done()
        self.assert_step_is_done(self.onboarding_1_step_1)
        self.assert_onboarding_is_not_done(self.onboarding_1)
        self.onboarding_1_step_2.with_company(self.company_2).action_set_just_done()
        self.assert_step_is_done(self.onboarding_1_step_2)
        self.assert_onboarding_is_done(self.onboarding_1)

        # is_onboarding_closed status is also company-independent
        self.onboarding_1.action_close()
        self.assertTrue(self.onboarding_1.current_progress_id.is_onboarding_closed)
        self.assertFalse(self.onboarding_1.with_company(self.company_1).current_progress_id.is_onboarding_closed)

    def test_onboarding_to_company_change(self):
        """Checks that changing onboarding to per-company resets completions states.
        """
        # Completing onboarding as company_1
        self.assertEqual(self.env.company, self.company_1)
        self.onboarding_1_step_1.action_set_just_done()
        self.onboarding_1_step_2.action_set_just_done()
        self.assert_onboarding_is_done(self.onboarding_1)

        # Updating onboarding to per-company
        self.onboarding_1.is_per_company = True
        # Required after progress reset (simulate role of controller)
        self.onboarding_1._search_or_create_progress()

        self.assert_onboarding_is_not_done(self.onboarding_1)

    def test_no_crash_on_multiple_progress_records(self):
        existing_progress = self.env['onboarding.progress'].search([
            ('onboarding_id', '=', self.onboarding_1.id), ('company_id', '=', False)
        ])
        self.assertEqual(len(existing_progress), 1)

        extra_progress = self.env['onboarding.progress'].create({
            'onboarding_id': self.onboarding_1.id,
            'company_id': False
        })

        self.env['onboarding.progress.step'].create([{
            'step_id': self.onboarding_1_step_1.id,
            'progress_id': progress.id
            } for progress in (existing_progress, extra_progress)
        ])

        nb_progress = self.env['onboarding.progress'].search([
            ('onboarding_id', '=', self.onboarding_1.id), ('company_id', '=', False)], count=True)
        nb_progress_steps = self.env['onboarding.progress.step'].search([
            ('step_id', '=', self.onboarding_1_step_1.id)], count=True)

        # Even though multiple onboarding progress (& steps) records exist
        self.assertEqual(nb_progress, 2)
        self.assertEqual(nb_progress_steps, 2)

        # no error is raised, and so we can interact
        _ = self.onboarding_1_step_1.current_progress_step_id
        self.onboarding_1_step_1.action_set_just_done()

        # Same with onboarding progress
        _ = self.onboarding_1.current_progress_id
        self.onboarding_1.action_close()
