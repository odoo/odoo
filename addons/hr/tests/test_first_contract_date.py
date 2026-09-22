from odoo.fields import Date
from odoo.tests import tagged

from odoo.addons.hr.tests.common import TestHrCommon


@tagged("post_install", "-at_install")
class TestFirstContractDate(TestHrCommon):
    """The kanban used to show `contract_date_start`, which is the start of the
    contract in force -- so a renewal made a ten-year employee look like a new
    hire. What a manager wants there is when the person joined.

    "Joined" stops at a break: `_get_first_version_date` treats a gap of four
    days or more between two versions as a new occupation, so an earlier stint
    does not count towards the current one.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee.version_id.write(
            {
                "date_version": Date.to_date("2015-01-01"),
                "date_start": Date.to_date("2015-01-01"),
            }
        )

    def _close_first_version_on(self, date_end):
        """Force a real break in the chain.

        `create_version` extends the previous version's `date_end` to the day
        before the new one, so adding a version never leaves a gap by itself --
        a break only exists once someone closes the earlier version, which is
        what happens when a person actually leaves and comes back.
        """
        self.env.flush_all()
        first = self.employee.version_ids.sorted("date_start")[0]
        first.write({"date_end": date_end})

    def _add_version(self, date_start, date_end=None):
        return self.employee.create_version(
            {
                "date_version": date_start,
                "date_start": date_start,
                "date_end": date_end,
                "name": f"Version from {date_start}",
                "wage": 5000.0,
            }
        )

    def test_a_renewal_does_not_reset_the_joining_date(self):
        """Contiguous versions are one occupation: the field shows its start."""
        self._add_version(Date.to_date("2016-01-01"))
        self.env.flush_all()
        self.employee.invalidate_recordset(["first_contract_date"])

        self.assertEqual(
            self.employee.first_contract_date,
            Date.to_date("2015-01-01"),
            "a renewal must not make a long-standing employee look new",
        )

    def test_a_break_of_four_days_starts_a_new_occupation(self):
        """And the other direction: a real break is a new joining date."""
        self._add_version(Date.to_date("2020-06-01"))
        self._close_first_version_on(Date.to_date("2015-12-31"))
        self.env.flush_all()
        self.employee.invalidate_recordset(["first_contract_date"])

        self.assertEqual(
            self.employee.first_contract_date,
            Date.to_date("2020-06-01"),
            "an earlier stint separated by years does not count towards this one",
        )

    def test_the_stored_value_follows_a_new_version(self):
        """It is a stored compute, so the write has to recompute it.

        A stored compute is the kind of field that reads correct by accident:
        without the right `depends` the first value is right and every later one
        is stale.
        """
        self.env.flush_all()
        self.employee.invalidate_recordset(["first_contract_date"])
        self.assertEqual(self.employee.first_contract_date, Date.to_date("2015-01-01"))

        self._add_version(Date.to_date("2021-01-01"))
        self._close_first_version_on(Date.to_date("2015-12-31"))
        self.env.flush_all()
        self.employee.invalidate_recordset(["first_contract_date"])

        self.assertEqual(
            self.employee.first_contract_date,
            Date.to_date("2021-01-01"),
            "adding a version after a break must move the stored value",
        )
