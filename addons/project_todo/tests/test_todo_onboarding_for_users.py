from odoo.tests.common import TransactionCase, new_test_user


class TestTodoOnboardingUsers(TransactionCase):
    """Test personal stages onboarding and onboarding task creation for project_todo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ProjectTaskTypeSudo = cls.env['project.task.type'].sudo()
        cls.ProjectTaskSudo = cls.env['project.task'].sudo()

    def _convert_user_group(self, user, remove_group, add_group):
        """Helper to safely change user groups in tests."""
        user.group_ids -= self.env.ref(f"base.group_{remove_group}")
        user.group_ids += self.env.ref(f"base.group_{add_group}")

    def test_onboarding_stages_and_task_created_for_new_internal_user(self):
        """Personal stages and onboarding task should be created for internal users upon creation."""
        internal_user = new_test_user(
            self.env,
            login="internal_user",
            groups="base.group_user",
        )
        onboarding_tasks = self.ProjectTaskSudo.search([('user_ids', 'in', internal_user.ids)])
        self.assertEqual(len(onboarding_tasks), 1, "Exactly 1 onboarding task should be created for internal users upon creation.")

    def test_onboarding_stages_and_task_created_when_user_becomes_internal(self):
        """Personal stages and onboarding task should be created when a portal/public user is converted to internal."""
        portal_user = new_test_user(
            self.env,
            login="portal_user",
            groups="base.group_portal",
        )
        onboarding_tasks = self.ProjectTaskSudo.search([('user_ids', 'in', portal_user.ids)])
        self.assertEqual(len(onboarding_tasks), 0, "Portal users should not receive onboarding tasks upon creation.")

        public_user = new_test_user(
            self.env,
            login="public_user",
            groups="base.group_public",
        )
        onboarding_tasks = self.ProjectTaskSudo.search([('user_ids', 'in', public_user.ids)])
        self.assertEqual(len(onboarding_tasks), 0, "Public users should not receive onboarding tasks upon creation.")

        # Convert portal user to internal
        self._convert_user_group(portal_user, "portal", "user")
        onboarding_tasks = self.ProjectTaskSudo.search([('user_ids', 'in', portal_user.ids)])
        self.assertEqual(len(onboarding_tasks), 1, "Exactly 1 onboarding task should be created when a portal user is converted to internal.")

        # Convert public user to internal
        self._convert_user_group(public_user, "public", "user")
        onboarding_tasks = self.ProjectTaskSudo.search([('user_ids', 'in', public_user.ids)])
        self.assertEqual(len(onboarding_tasks), 1, "Exactly 1 onboarding task should be created when a public user is converted to internal.")

    def test_onboarding_stages_created_once_on_repeated_internal_portal_toggle(self):
        """Repeatedly toggling internal ↔ portal or internal ↔ public should not create duplicate personal stages or onboarding tasks."""
        toggle_internal_user = new_test_user(
            self.env,
            login="toggle_internal_user",
            groups="base.group_user",
        )
        onboarding_tasks = self.ProjectTaskSudo.search([('user_ids', 'in', toggle_internal_user.ids)])
        self.assertEqual(len(onboarding_tasks), 1, "Exactly 1 onboarding task should be created for internal users upon creation.")

        # Convert internal user to portal
        self._convert_user_group(toggle_internal_user, "user", "portal")

        # Convert back to internal
        self._convert_user_group(toggle_internal_user, "portal", "user")

        onboarding_tasks = self.ProjectTaskSudo.search([('user_ids', 'in', toggle_internal_user.ids)])
        self.assertEqual(len(onboarding_tasks), 1, "Onboarding task count should remain unchanged when user is converted to internal from portal.")

        # Convert internal user to public
        self._convert_user_group(toggle_internal_user, "user", "public")

        # Convert back to internal user
        self._convert_user_group(toggle_internal_user, "public", "user")

        onboarding_tasks = self.ProjectTaskSudo.search([('user_ids', 'in', toggle_internal_user.ids)])
        self.assertEqual(len(onboarding_tasks), 1, "Onboarding task count should remain unchanged when user is converted back to internal from public.")
