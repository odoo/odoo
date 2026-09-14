import json
from datetime import datetime, timedelta

from freezegun import freeze_time

from odoo.tests.common import HttpCase, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKioskPinThrottle(TransactionCase):
    """A four-digit PIN behind a public route needs a server-side cost per guess.

    The keypad's back-off lives in `pin_code.js`, which runs in the caller's
    browser. `/hr_attendance/manual_selection` is `auth="public"`, so a request
    that never loads the keypad never pays it, and the route answers with the
    employee's data on success and `{}` on failure -- a clean oracle over ten
    thousand possibilities.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {"name": "Pin Ltd", "attendance_kiosk_use_pin": True}
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Pinned", "company_id": cls.company.id, "pin": "4242"}
        )

    def test_the_right_pin_opens_it(self):
        self.assertTrue(self.employee._check_attendance_pin("4242"))

    def test_an_empty_pin_never_opens_it(self):
        self.assertFalse(self.employee._check_attendance_pin(""))
        self.assertFalse(self.employee._check_attendance_pin(False))

    def test_the_first_few_mistypes_cost_nothing(self):
        for _ in range(3):
            self.assertFalse(self.employee._check_attendance_pin("0000"))
            self.assertEqual(self.employee._attendance_pin_retry_delay(), 0)

    def test_the_delay_doubles_and_then_caps(self):
        with freeze_time(datetime(2026, 9, 1, 10, 0, 0)):
            delays = []
            for _ in range(9):
                self.employee._check_attendance_pin("0000")
                delays.append(self.employee._attendance_pin_retry_delay())
        self.assertEqual(
            delays,
            [0, 0, 0, 2, 4, 8, 16, 32, 60],
            "a caller that retries on a timer must not sit at the first delay "
            "forever: attempts made while throttled have to count too",
        )

    def test_a_throttled_employee_is_refused_even_with_the_right_pin(self):
        with freeze_time(datetime(2026, 9, 1, 10, 0, 0)):
            for _ in range(4):
                self.employee._check_attendance_pin("0000")
            self.assertFalse(self.employee._check_attendance_pin("4242"))

    def test_the_delay_expires_and_success_clears_the_count(self):
        start = datetime(2026, 9, 1, 10, 0, 0)
        with freeze_time(start):
            for _ in range(4):
                self.employee._check_attendance_pin("0000")
        with freeze_time(start + timedelta(minutes=5)):
            self.assertTrue(self.employee._check_attendance_pin("4242"))
        self.assertEqual(self.employee.attendance_pin_failure_count, 0)
        self.assertFalse(self.employee.attendance_pin_retry_after)


@tagged("post_install", "-at_install", "hr_attendance_kiosk")
class TestKioskPinRouteThrottle(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {"name": "Pin Route Ltd", "attendance_kiosk_use_pin": True}
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Route Pinned", "company_id": cls.company.id, "pin": "4242"}
        )

    def _attempt(self, pin):
        response = self.url_open(
            "/hr_attendance/manual_selection",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "token": self.company.sudo().attendance_kiosk_key,
                        "employee_id": self.employee.id,
                        "pin_code": pin,
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        return response.json().get("result")

    def _assert_refused(self, pin, message=None):
        # A refusal is `{"status": "error"}` across the kiosk surface; asserting
        # falsiness instead passed for any object the route might return.
        self.assertEqual(self._attempt(pin).get("status"), "error", message)

    def test_guessing_through_the_route_is_throttled(self):
        for _ in range(4):
            self._assert_refused("0000")
        self._assert_refused(
            "4242",
            "the route must apply the same cost the keypad only pretends to",
        )
        self.assertTrue(self.employee.sudo().attendance_pin_retry_after)

    def test_the_route_still_works_without_pins_configured(self):
        self.company.sudo().attendance_kiosk_use_pin = False
        self.assertTrue(self._attempt(""))
