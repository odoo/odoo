# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestOnboardingCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create two companies including Mitchell
        cls.user_admin = cls.env.ref('base.user_admin')

        cls.company_1 = cls.user_admin.company_id
        cls.company_2 = cls.env['res.company'].create({
            'currency_id': cls.env.ref('base.AUD').id,
            'name': 'New Test Company',
        })
        cls.user_admin.company_ids |= cls.company_2

        cls.onboarding_1 = cls.env['onboarding.onboarding'].create([
            {
                'name': 'Test Onboarding 1',
                'is_per_company': False,
                'route_name': 'onboarding1'
            }
        ])

        # create a fake action for step opening
        cls.action_fake_open_onboarding_step = cls.env['ir.actions.act_window'].create({
            'name': 'action_fake_open_onboarding_step',
            'res_model': 'onboarding.onboarding',
        })

        # Add two steps
        cls.onboarding_1_step_1, cls.onboarding_1_step_2 = cls.env['onboarding.onboarding.step'].create([
            {
                'title': f'Test Onboarding 1 - Step {step_n}',
                'onboarding_id': cls.onboarding_1.id,
                'panel_step_open_action_name': 'action_fake_open_onboarding_step',
            }
            for step_n in range(1, 3)
        ])

        # Create progress records as would happen through the controller
        cls.onboarding_1.with_company(cls.company_1)._search_or_create_progress()

    def assert_step_is_done(self, step, also_with_company=None):
        self.assertIn(
            step.current_progress_step_id.step_state, {'done', 'just_done'},
            f'Expected done-like current state for step {step.id} for {step.env.company}')
        self.assertEqual(step.current_progress_step_id.step_state, step.current_step_state)
        if also_with_company:
            self.assert_step_is_done(step.with_company(also_with_company))

    def assert_step_is_not_done(self, step, also_with_company=None):
        self.assertIn(
            step.current_progress_step_id.step_state, {'not_done', False},
            f'Expected "not_done" current state for step {step.id} for {step.env.company}')
        self.assertEqual(step.current_step_state, 'not_done')
        if also_with_company:
            self.assert_step_is_not_done(step.with_company(also_with_company))

    def assert_onboarding_is_done(self, onboarding, also_with_company=None):
        self.assertIn(
            onboarding.current_progress_id.onboarding_state, {'done', 'just_done'},
            f'Expected done-like current state for onboarding {onboarding.name} '
            f'for {onboarding.env.company}')
        self.assertEqual(onboarding.current_progress_id.onboarding_state,
                         onboarding.current_onboarding_state)
        if also_with_company:
            self.assert_onboarding_is_done(onboarding.with_company(also_with_company))

    def assert_onboarding_is_not_done(self, onboarding, also_with_company=None):
        self.assertEqual(
            onboarding.current_progress_id.onboarding_state, 'not_done',
            f'Expected "not_done" current state for onboarding {onboarding.name} '
            f'for {onboarding.env.company}')
        self.assertEqual(onboarding.current_onboarding_state, 'not_done')
        if also_with_company:
            self.assert_onboarding_is_not_done(onboarding.with_company(also_with_company))

    def activate_company(self, company):
        self.onboarding_1_step_1 = self.onboarding_1_step_1.with_company(company)
        self.onboarding_1_step_2 = self.onboarding_1_step_2.with_company(company)
        self.onboarding_1 = self.onboarding_1.with_company(company)
