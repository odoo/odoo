# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TransactionCaseOnboarding(TransactionCase):
    def assert_step_is_done(self, step, also_with_company=None):
        self.assertIn(
            step.current_progress_step_id.step_state, {'done', 'just_done'},
            f'Expected done-like current state for step {step.id} for {step.env.company.name}')
        self.assertEqual(step.current_progress_step_id.step_state, step.current_step_state)
        if also_with_company:
            self.assert_step_is_done(step.with_company(also_with_company))

    def assert_step_is_not_done(self, step, also_with_company=None):
        self.assertIn(
            step.current_progress_step_id.step_state, {'not_done', False},
            f'Expected "not_done" current state for step {step.id} for {step.env.company.name}')
        self.assertEqual(step.current_step_state, 'not_done')
        if also_with_company:
            self.assert_step_is_not_done(step.with_company(also_with_company))

    def assert_onboarding_is_done(self, onboarding, also_with_company=None):
        self.assertIn(
            onboarding.current_progress_id.onboarding_state, {'done', 'just_done'},
            f'Expected done-like current state for onboarding "{onboarding.name}" '
            f'for "{onboarding.env.company.name}"')
        self.assertEqual(onboarding.current_progress_id.onboarding_state,
                         onboarding.current_onboarding_state)
        if also_with_company:
            self.assert_onboarding_is_done(onboarding.with_company(also_with_company))

    def assert_onboarding_is_not_done(self, onboarding, also_with_company=None):
        self.assertIn(
            onboarding.current_progress_id.onboarding_state, {'not_done', False},
            f'Expected `"not_done"` or `False` current state for onboarding {onboarding.name} '
            f'for {onboarding.env.company.name}')
        self.assertEqual(onboarding.current_onboarding_state, 'not_done')
        if also_with_company:
            self.assert_onboarding_is_not_done(onboarding.with_company(also_with_company))
