from datetime import timedelta

from odoo.tests import tagged

from .common import HrPresenceCase


@tagged("post_install", "-at_install")
class TestMultiCompany(HrPresenceCase):
    """The sweep used to read self.env.company and search that company alone, so
    every other company was never computed -- and never reset either. The
    compute read self.env.company too, which put one cache entry in front of two
    readers who disagreed about the answer.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other = cls.env["res.company"].create({"name": "Other Presence Co"})
        cls.other_calendar = cls._make_calendar(cls.other, "UTC")
        cls.other.write(
            {
                "resource_calendar_id": cls.other_calendar.id,
                "hr_presence_control_ip": True,
                "hr_presence_control_ip_list": "10.0.0.9",
            }
        )
        cls.here = cls._make_employee("here")
        cls.there = cls._make_employee(
            "there", company=cls.other, calendar=cls.other_calendar
        )

    def test_the_sweep_reaches_a_company_the_cron_user_does_not_sit_in(self):
        self.assertNotEqual(
            self.there.company_id,
            self.env.company,
            "fixture: the employee must be outside the sweeping user's company",
        )
        self.there.hr_presence_state_display = "present"
        self.env["hr.employee"].with_company(self.company)._check_presence()
        self.assertEqual(
            self.there.hr_presence_state_display,
            "absent",
            "the sweep used to search self.env.company alone",
        )

    def test_evidence_of_another_company_is_not_left_standing(self):
        """Four booleans were reset by whichever sweep reached them; a company
        the sweep never reached kept yesterday's answer indefinitely."""
        self.there.hr_presence_ip_date = self._today_for(self.there) - timedelta(days=1)
        self.env["hr.employee"].with_company(self.company)._check_presence()
        self.assertEqual(self.there.hr_presence_state, "absent")

    def test_the_state_does_not_depend_on_who_is_reading_it(self):
        self.here.hr_presence_ip_date = self._today_for(self.here)
        self.env.invalidate_all()
        read_at_home = self.here.with_company(self.company).hr_presence_state
        self.env.invalidate_all()
        read_from_abroad = self.here.with_company(self.other).hr_presence_state
        self.assertEqual(read_at_home, "present")
        self.assertEqual(
            read_from_abroad,
            "present",
            "the employee's own company decides, not the reader's",
        )

    def test_one_cache_entry_cannot_serve_two_readers_a_different_answer(self):
        self.here.hr_presence_ip_date = self._today_for(self.here)
        self.env.invalidate_all()
        first = self.here.with_company(self.other).hr_presence_state
        second = self.here.with_company(self.company).hr_presence_state
        self.assertEqual(
            first,
            second,
            "reading order used to decide the answer for everyone in the transaction",
        )
        # Equality alone would hold just as well if both readers were wrong, so
        # say which answer they have to agree on.
        self.assertEqual(first, "present")

    def test_each_company_keeps_its_own_valid_ip_list(self):
        self.assertEqual(
            self.company._hr_presence_valid_ips(), {"10.0.0.1", "10.0.0.2"}
        )
        self.assertEqual(self.other._hr_presence_valid_ips(), {"10.0.0.9"})
