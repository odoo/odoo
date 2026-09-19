from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import freeze_time

from odoo.addons.account.tests.common_report_engine import TestAccountReportsCommon


@freeze_time("2024-01-01")
@tagged("post_install", "-at_install")
class TestKpiProvider(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company.write(
            {
                "vat": "38972223422",
                "phone_ids": [
                    Command.create({"number": "555-555-5555", "type": "landline"})
                ],
                "email": "test@example.com",
            }
        )
        cls.return_types = cls.env["account.return.type"].create(
            [
                {
                    "name": "Return with a report without a root report",
                    "report_id": cls.env.ref("account.generic_tax_report").id,
                    "deadline_start_date": "2024-01-01",
                },
                {
                    "name": "Return with a root report",
                    "report_id": cls.env.ref("account.followup_report").id,
                    "deadline_start_date": "2024-01-01",
                },
                {
                    "name": "Return without a report",
                    "deadline_start_date": "2024-01-01",
                },
            ]
        )

        def generate_all_returns(
            account_return_type, country_code, main_company, tax_unit=None
        ):
            for return_type in cls.return_types:
                return_type._try_create_returns_for_fiscal_year(main_company, tax_unit)

        with patch.object(
            cls.registry["account.return.type"],
            "_generate_all_returns",
            generate_all_returns,
        ):
            cls.env.company.account_config_id.account_opening_date = "2024-01-01"

    def test_kpi_summary(self):
        self.assertCountEqual(
            self.env["kpi.provider"].get_account_reports_kpi_summary(),
            [
                {
                    "id": "account_return.account_generic_tax_report",
                    "name": "Generic Tax report",
                    "type": "return_status",
                    "value": "to_do",
                },
                {
                    "id": "account_return.account_partner_ledger_report",
                    "name": "Follow-Up Report",
                    "type": "return_status",
                    "value": "to_do",
                },
                {
                    "id": "account_return.return_without_a_report",
                    "name": "Return without a report",
                    "type": "return_status",
                    "value": "to_do",
                },
            ],
        )

    def test_kpi_summary_resolves_today_in_the_users_timezone(self):
        """The deadline comparison is made against the *user's* today.

        It used to be made against a date PostgreSQL derived by reading the
        naive server clock as wall-clock time in the user's zone and rendering
        the result in the session's zone -- which is the conversion backwards,
        and dependent on a session setting Odoo never sets.
        """
        self.env.cr.execute(
            "UPDATE account_return SET date_deadline = '2024-01-02', is_completed = false"
        )
        self.env.invalidate_all()

        with freeze_time("2024-01-01 20:00:00"):
            # 2024-01-01 in Los Angeles: the deadline is still ahead
            self.env.user.tz = "America/Los_Angeles"
            self.env.flush_all()
            values = {
                kpi["value"]
                for kpi in self.env["kpi.provider"].get_account_reports_kpi_summary()
            }
            self.assertEqual(values, {"to_do"})

            # already 2024-01-02 in Tokyo: the same deadline is reached
            self.env.user.tz = "Asia/Tokyo"
            self.env.flush_all()
            values = {
                kpi["value"]
                for kpi in self.env["kpi.provider"].get_account_reports_kpi_summary()
            }
            self.assertEqual(values, {"late"})

    def test_kpi_summary_with_a_timezone_postgresql_does_not_know(self):
        """Odoo's tz dropdown offers every zoneinfo name; PostgreSQL knows a
        subset, and this query used to hand it the stored value.

        The name is chosen rather than discovered. Diffing the two catalogues and
        asserting the difference is non-empty made the test depend on the host:
        on a build where they agree -- which current PostgreSQL and Python do --
        it failed on its own premise instead of exercising the path.
        """
        self.env.cr.execute("SELECT name FROM pg_timezone_names")
        pg_names = {name for [name] in self.env.cr.fetchall()}
        offered = dict(
            self.env["res.users"]._fields["tz"]._description_selection(self.env)
        )

        # Prefer a name the two catalogues really disagree on; fall back to a
        # legacy alias, which is the shape that used to break.
        divergent = sorted(set(offered) - pg_names)
        tz_name = next(
            (name for name in (*divergent, "Asia/Calcutta") if name in offered),
            None,
        )
        self.assertTrue(tz_name, "the tz selection offered nothing to test with")

        self.env.user.tz = tz_name
        self.env.flush_all()
        self.assertTrue(self.env["kpi.provider"].get_account_reports_kpi_summary())

    def test_the_kpi_summary_never_hands_a_timezone_name_to_postgresql(self):
        """The invariant that makes every zone name safe, and the only part of it
        that can be checked on a host whose catalogues agree: the zone is resolved
        in Python, so no AT TIME ZONE ever carries the stored value."""
        executed = []
        original_execute = type(self.env.cr).execute

        def spy(cr, query, params=None, *args, **kwargs):
            executed.append(str(query))
            return original_execute(cr, query, params, *args, **kwargs)

        self.env.user.tz = "Asia/Tokyo"
        self.env.flush_all()
        with patch.object(type(self.env.cr), "execute", spy):
            self.env["kpi.provider"].get_account_reports_kpi_summary()

        self.assertTrue(executed, "the spy caught nothing")
        for query in executed:
            self.assertNotIn(
                "AT TIME ZONE",
                query.upper(),
                "the timezone must be resolved in Python, not by PostgreSQL",
            )
