from psycopg import IntegrityError

from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("at_install", "-post_install")
class TestResourceResourceCrud(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "CRUD Calendar", "tz": "Europe/Brussels"}
        )
        cls.user = cls.env["res.users"].create(
            {"name": "Resource User", "login": "res_crud_user", "tz": "Asia/Tokyo"}
        )
        cls.resource = cls.env["resource.resource"].create(
            {"name": "Machine", "calendar_id": cls.calendar.id}
        )

    def test_copy_appends_copy_to_name(self):
        copy = self.resource.copy()
        self.assertIn("(copy)", str(copy.name))

    def test_create_inherits_tz_from_calendar(self):
        resource = self.env["resource.resource"].create(
            {"name": "Machine 2", "calendar_id": self.calendar.id}
        )
        self.assertEqual(resource.tz, "Europe/Brussels")

    def test_write_idempotence_skips_noop(self):
        result = self.resource.with_context(check_idempotence=True).write(
            {"name": self.resource.name}
        )
        self.assertTrue(result)

    def test_compute_avatar_follows_user(self):
        self.resource.user_id = self.user
        self.assertEqual(self.resource.avatar_128, self.user.avatar_128)

    def test_onchange_company_sets_calendar(self):
        resource = self.env["resource.resource"].new(
            {"company_id": self.env.company.id}
        )
        resource._onchange_company_id()
        self.assertEqual(resource.calendar_id, self.env.company.resource_calendar_id)

    def test_choosing_a_user_does_not_move_the_work_zone(self):
        resource = self.env["resource.resource"].create(
            {"name": "Deployed", "tz": "America/Mazatlan"}
        )
        self.user.tz = "Europe/Brussels"
        resource.user_id = self.user
        self.assertEqual(resource.tz, "America/Mazatlan")

    @mute_logger("odoo.db.cursor")
    def test_create_zero_time_efficiency_violates_check(self):
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env["resource.resource"].create(
                {
                    "name": "Zero Efficiency",
                    "calendar_id": self.calendar.id,
                    "time_efficiency": 0,
                }
            )
            self.env["resource.resource"].flush_model()
