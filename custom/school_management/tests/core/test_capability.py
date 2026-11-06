from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestSystemCapabilities(TransactionCase):
    """Verify the university.capability model, its access rights and the
    admin-only System -> Capabilities & Roadmap menu."""

    def setUp(self):
        super().setUp()
        self.Capability = self.env["university.capability"]
        self.Users = self.env["res.users"].sudo()

        self.g_user = self.env.ref("school_management.group_school_user")
        self.g_teacher = self.env.ref("school_management.group_school_teacher")
        self.g_admin = self.env.ref("school_management.group_school_admin")

        self.capability_menu = self.env.ref("school_management.menu_university_capability")
        self.system_menu = self.env.ref("school_management.menu_university_system")

    def _make_user(self, login, *groups):
        return self.Users.with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": "%s@example.com" % login,
                "group_ids": [(6, 0, [g.id for g in groups])],
            }
        )

    # ------------------------------------------------------------------ #
    # Seed data present and coherent
    # ------------------------------------------------------------------ #
    def test_seed_data_loaded(self):
        caps = self.Capability.search([])
        self.assertGreaterEqual(len(caps), 10)
        self.assertTrue(caps.filtered(lambda c: c.status == "active"))
        self.assertTrue(caps.filtered(lambda c: c.status == "planned"))
        self.assertTrue(all(c.name for c in caps))
        self.assertTrue(all(c.category for c in caps))

    def test_seed_phase_assignment(self):
        phase1 = self.Capability.search([("phase", "=", 1)])
        self.assertTrue(phase1)
        self.assertTrue(all(c.status == "active" for c in phase1))

    # ------------------------------------------------------------------ #
    # Read access for all school staff (dashboard must render it)
    # ------------------------------------------------------------------ #
    def test_teacher_can_read_capabilities(self):
        user = self._make_user("cap_read_teacher", self.g_teacher)
        records = self.Capability.with_user(user).search([], limit=5)
        self.assertTrue(records)

    def test_plain_school_user_can_read_capabilities(self):
        user = self._make_user("cap_read_user", self.g_user)
        records = self.Capability.with_user(user).search([], limit=5)
        self.assertTrue(records)

    # ------------------------------------------------------------------ #
    # Write/create restricted to admins
    # ------------------------------------------------------------------ #
    def test_teacher_cannot_create_capability(self):
        user = self._make_user("cap_write_teacher", self.g_teacher)
        with self.assertRaises(AccessError):
            self.Capability.with_user(user).create({"name": "Nope"})

    def test_admin_can_create_and_update_capability(self):
        user = self._make_user("cap_admin", self.g_admin)
        cap = self.Capability.with_user(user).create(
            {
                "name": "eLearning Platform",
                "category": "academic",
                "status": "planned",
                "phase": 3,
            }
        )
        cap.with_user(user).write({"status": "development"})
        self.assertEqual(cap.status, "development")

    # ------------------------------------------------------------------ #
    # Menu is admin/system only (no teacher access)
    # ------------------------------------------------------------------ #
    def test_capability_menu_groups(self):
        system = self.env.ref("base.group_system")
        groups = self.capability_menu.group_ids
        self.assertIn(self.g_admin, groups)
        self.assertIn(system, groups)
        self.assertNotIn(self.g_teacher, groups)
        self.assertNotIn(self.g_user, groups)

    def test_capability_menu_under_system_parent(self):
        self.assertEqual(self.capability_menu.parent_id, self.system_menu)
        action = self.env.ref("school_management.action_university_capability")
        self.assertEqual(action.res_model, "university.capability")
        self.assertEqual(self.capability_menu.action, action)