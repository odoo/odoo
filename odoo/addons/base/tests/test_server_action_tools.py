import datetime

from odoo.exceptions import UserError
from odoo.tests import TransactionCase
from odoo.tools.server_action_tools import ServerActionTools


class TestServerActionTools(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tools = ServerActionTools(cls.env)
        Partner = cls.env["res.partner"]
        cls.agro = Partner.create({"name": "Agro Sur"})
        cls.agro_norte = Partner.create({"name": "Agro Norte"})
        cls.exact = Partner.create({"name": "Semillas"})
        Partner.create({"name": "Semillas del Valle"})

    def test_an_exact_name_wins_over_the_partial_ones(self):
        self.assertEqual(self.tools.find("res.partner", "semillas"), self.exact)

    def test_a_single_partial_match_is_accepted(self):
        self.assertEqual(self.tools.find("res.partner", "sur"), self.agro)

    def test_several_matches_are_refused_by_name(self):
        with self.assertRaises(UserError) as caught:
            self.tools.find("res.partner", "agro")
        self.assertIn("Agro Norte", str(caught.exception))

    def test_an_archived_record_is_found_only_when_asked_for(self):
        old = self.env["res.partner"].create(
            {"name": "Semillera Vieja", "active": False}
        )
        self.assertFalse(self.tools.find("res.partner", "Semillera Vieja"))
        self.assertEqual(
            self.tools.find("res.partner", "Semillera Vieja", archived=True), old
        )

    def test_nothing_named_is_nothing_found(self):
        self.assertFalse(self.tools.find("res.partner", "  "))
        self.assertFalse(self.tools.find("res.partner", "zzz-no-such"))

    def test_a_pattern_character_is_literal(self):
        self.assertFalse(self.tools.find("res.partner", "Agro%"))
        self.assertEqual(self.tools.like(" 50%_off "), "50\\%\\_off")

    def test_a_date_and_a_local_datetime(self):
        self.assertEqual(
            self.tools.date("2026-09-21 10:00"), datetime.date(2026, 9, 21)
        )
        self.assertIsNone(self.tools.date(""))
        user = self.env.user
        user.tz = "America/Mexico_City"
        self.assertEqual(
            ServerActionTools(self.env).datetime("2026-09-21 10:00"),
            datetime.datetime(2026, 9, 21, 16, 0),
        )
        self.assertEqual(
            ServerActionTools(self.env).datetime("2026-09-21", default_time="09:00"),
            datetime.datetime(2026, 9, 21, 15, 0),
        )
        self.assertEqual(
            self.tools.datetime("2026-09-21 10:00", tz="Europe/Madrid"),
            datetime.datetime(2026, 9, 21, 8, 0),
        )
        with self.assertRaises(UserError):
            self.tools.datetime("mañana")

    def test_a_local_datetime_on_a_dst_edge_reads_standard_time(self):
        for local, utc in (
            ("2026-11-01 01:30", datetime.datetime(2026, 11, 1, 6, 30)),
            ("2026-03-08 02:30", datetime.datetime(2026, 3, 8, 7, 30)),
        ):
            with self.subTest(local=local):
                self.assertEqual(self.tools.datetime(local, tz="America/New_York"), utc)

    def test_lines_and_json_objects(self):
        self.assertEqual(
            self.tools.lines(["Urea | 2 | kg", "Glifosato | x", "", " | 3"]),
            [
                {"name": "Urea", "quantity": 2.0, "unit": "kg"},
                {"name": "Glifosato", "quantity": 1.0, "unit": ""},
            ],
        )
        self.assertEqual(self.tools.json('{"a": 1}'), {"a": 1})
        with self.assertRaises(UserError):
            self.tools.json("[1, 2]")

    def test_a_server_action_reaches_them_as_tools(self):
        action = self.env["ir.actions.server"].create(
            {
                "name": "Rename by tools",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "state": "code",
                "code": "tools.find('res.partner', 'Agro Sur').write({'name': 'Agro Sureste'})",
            }
        )
        action.run()
        self.assertEqual(self.agro.name, "Agro Sureste")
