from odoo.tests.common import TransactionCase, new_test_user


class TestTodoOnboardingUsers(TransactionCase):
    """Test personal stages onboarding and onboarding task creation for project_todo."""

    def test_onboarding_stages_and_task_created_for_new_users(self):
        """Personal stages and onboarding task should be created for internal users upon creation."""
        ProjectTaskSudo = self.env["project.task"].sudo()

        internal_user = new_test_user(
            self.env,
            login="internal_user",
            groups="base.group_user",
        )
        onboarding_tasks = ProjectTaskSudo.search([('user_ids', 'in', internal_user.ids)])

        self.assertEqual(len(onboarding_tasks), 1, "Exactly 1 onboarding task should be created for internal users upon creation.")
        self.assertFalse(onboarding_tasks.project_id, "Onboarding task should not be linked to any project.")
        portal_user = new_test_user(
            self.env,
            login="portal_user",
            groups="base.group_portal",
        )
        onboarding_tasks = ProjectTaskSudo.search([('user_ids', 'in', portal_user.ids)])
        self.assertEqual(len(onboarding_tasks), 0, "Portal users should not receive onboarding tasks upon creation.")

        public_user = new_test_user(
            self.env,
            login="public_user",
            groups="base.group_public",
        )
        onboarding_tasks = ProjectTaskSudo.search([('user_ids', 'in', public_user.ids)])
        self.assertEqual(len(onboarding_tasks), 0, "Public users should not receive onboarding tasks upon creation.")

        project = self.env['project.project'].create({'name': 'Test Project'})
        other_internal_user = new_test_user(
            self.env,
            login="other_internal_user",
            groups="base.group_user",
            context={'default_project_id': project.id},
        )
        onboarding_tasks = ProjectTaskSudo.search([('user_ids', 'in', other_internal_user.ids)])
        self.assertEqual(len(onboarding_tasks), 1, "Exactly 1 onboarding task should be created for internal users upon creation.")
        self.assertFalse(onboarding_tasks.project_id, "Onboarding task should not be linked to any project.")
