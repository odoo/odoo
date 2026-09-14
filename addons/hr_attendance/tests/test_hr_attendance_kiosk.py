import json
from unittest.mock import patch

from odoo import Command
from odoo.http import Request
from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install", "hr_attendance_kiosk")
class TestHrAttendanceKiosk(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_A = cls.env["res.company"].create({"name": "company_A"})
        cls.company_B = cls.env["res.company"].create({"name": "company_B"})

        cls.department_A = cls.env["hr.department"].create(
            {"name": "department_A", "company_id": cls.company_B.id}
        )

        cls.employee_A = cls.env["hr.employee"].create(
            {
                "name": "employee_A",
                "company_id": cls.company_B.id,
                "department_id": cls.department_A.id,
            }
        )
        cls.department_B = cls.env["hr.department"].create(
            {"name": "department_B", "company_id": cls.company_A.id}
        )
        cls.employee_B = cls.env["hr.employee"].create(
            {
                "name": "employee_B",
                "company_id": cls.company_A.id,
                "department_id": cls.department_B.id,
            }
        )

    def test_employee_count_kiosk(self):
        with patch.object(Request, "render", return_value=None) as render:
            self.url_open(self.company_B.attendance_kiosk_url)

        render.assert_called_once()
        _template, kiosk_info = render.call_args[0]
        kiosk_info = kiosk_info["kiosk_backend_info"]
        self.assertEqual(kiosk_info["company_name"], "company_B")
        self.assertEqual(kiosk_info["departments"][0]["count"], 1)


@tagged("post_install", "-at_install", "hr_attendance_kiosk")
class TestKioskRouteAuthorisation(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Kiosk Auth"})
        cls.other_company = cls.env["res.company"].create({"name": "Kiosk Other"})
        cls.badged = cls.env["hr.employee"].create(
            {
                "name": "Already Badged",
                "company_id": cls.company.id,
                "barcode": "EXISTINGBADGE",
            }
        )
        cls.unbadged = cls.env["hr.employee"].create(
            {"name": "No Badge Yet", "company_id": cls.company.id}
        )

    def _call(self, route, **params):
        response = self.url_open(
            route,
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "params": params}),
            headers={"Content-Type": "application/json"},
        )
        return response.json().get("result")

    @property
    def _token(self):
        return self.company.sudo().attendance_kiosk_key

    def test_set_badge_does_not_reassign_an_existing_badge(self):
        result = self._call(
            "/hr_attendance/set_badge",
            employee_id=self.badged.id,
            badge="STOLENBADGE",
            token=self._token,
        )
        self.assertEqual(result.get("status"), "error")
        self.assertEqual(
            self.badged.sudo().barcode,
            "EXISTINGBADGE",
            "the existing badge must survive the call",
        )

    def test_set_badge_is_not_granted_by_the_token_alone(self):
        result = self._call(
            "/hr_attendance/set_badge",
            employee_id=self.unbadged.id,
            badge="NEWBADGE",
            token=self._token,
        )
        self.assertNotEqual(result.get("status"), "success")
        self.assertFalse(
            self.unbadged.sudo().barcode,
            "possession of the kiosk token is not authority to assign a badge",
        )

    def test_set_badge_works_for_a_user_who_may_write(self):
        self.authenticate("admin", "admin")
        self.env["res.users"].browse(2).company_ids = [
            Command.link(self.company.id),
        ]
        self.env.flush_all()
        result = self._call(
            "/hr_attendance/set_badge",
            employee_id=self.unbadged.id,
            badge="NEWBADGE",
            token=self._token,
        )
        self.assertEqual(result.get("status"), "success")
        self.assertEqual(self.unbadged.sudo().barcode, "NEWBADGE")

    def test_set_settings_targets_the_company_the_token_names(self):
        self.authenticate("admin", "admin")
        admin = self.env["res.users"].browse(2)
        admin.company_ids = [
            Command.link(self.company.id),
            Command.link(self.other_company.id),
        ]
        admin.company_id = self.other_company
        before = self.other_company.attendance_kiosk_mode
        self.env.flush_all()
        self._call("/hr_attendance/set_settings", token=self._token, mode="manual")
        self.assertEqual(self.company.attendance_kiosk_mode, "manual")
        self.assertEqual(
            self.other_company.attendance_kiosk_mode,
            before,
            "the caller's own company must be left alone",
        )

    def test_set_settings_rejects_a_mode_that_is_not_one(self):
        self.authenticate("admin", "admin")
        self.env["res.users"].browse(2).company_ids = [Command.link(self.company.id)]
        before = self.company.attendance_kiosk_mode
        self.env.flush_all()
        result = self._call(
            "/hr_attendance/set_settings", token=self._token, mode="not_a_mode"
        )
        self.assertEqual(result.get("status"), "error")
        self.assertEqual(self.company.attendance_kiosk_mode, before)

    def test_an_invalid_token_reaches_nothing(self):
        # Every kiosk route answers a refusal the same way, so the assertion is
        # on the status rather than on truthiness: `{}` and `{"status": ...}`
        # are both objects, and a route that starts returning the second while
        # a test asks for the first is not a behaviour change worth a red.
        result = self._call(
            "/hr_attendance/set_badge",
            employee_id=self.unbadged.id,
            badge="X",
            token="not-a-token",
        )
        self.assertEqual(result.get("status"), "error")
        self.assertFalse(self.unbadged.sudo().barcode)


@tagged("post_install", "-at_install", "hr_attendance_kiosk")
class TestKioskSettingsModeIsNotSelfServe(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Trial Mode Co"})

    def _kiosk_mode_for(self, query=""):
        with patch.object(Request, "render", return_value=None) as render:
            self.url_open(self.company.sudo().attendance_kiosk_url + query)
        render.assert_called_once()
        _template, info = render.call_args[0]
        return info["kiosk_backend_info"]["kiosk_mode"]

    def test_an_anonymous_visitor_gets_the_configured_kiosk_mode(self):
        self.assertEqual(self._kiosk_mode_for(), self.company.attendance_kiosk_mode)

    def test_from_trial_mode_is_supplied_by_the_caller(self):
        """`from_trial_mode` arrives from the query string, so anyone holding the
        kiosk URL can ask for the settings screen.

        The token is meant to be pinned to a shared device, and the settings
        screen is where employee creation and badge assignment live. This test
        records what the flag actually does; the routes behind it are what has
        to hold, and `TestKioskRouteAuthorisation` is where that is asserted.
        """
        self.assertEqual(
            self._kiosk_mode_for("?from_trial_mode=True"),
            "settings",
            "an anonymous caller reaches the settings screen just by asking",
        )
