from datetime import date

from odoo.tests.common import TransactionCase


class TestWorkEntryInvariants(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Invariants Co"})
        cls.env.user.company_ids = [(4, cls.company.id)]
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Invariants Employee",
                "company_id": cls.company.id,
                "contract_date_start": "2023-01-01",
                "date_version": "2023-01-01",
            }
        )
        cls.work_entry_type = cls.env["hr.work.entry.type"].create(
            {"name": "Paid Attendance", "code": "INV_ATTEND", "amount_rate": 2.0}
        )

    def _create(self, **vals):
        return self.env["hr.work.entry"].create(
            {
                "employee_id": self.employee.id,
                "work_entry_type_id": self.work_entry_type.id,
                "date": date(2024, 6, 10),
                "duration": 8.0,
                **vals,
            }
        )

    def test_validated_entry_is_not_flagged_by_a_later_same_day_entry(self):
        validated = self._create(duration=8.0)
        self.assertTrue(validated.action_validate())
        self.assertEqual(validated.state, "validated")

        overflowing = self._create(duration=20.0)

        self.assertEqual(
            validated.state,
            "validated",
            "A validated work entry must keep its state when a later entry pushes "
            "the day over 24h: only the entry that is still open may be flagged. "
            "If this fails, _mark_conflicting_work_entries has lost the "
            "state NOT IN ('validated', 'cancelled') predicate on its outer "
            "SELECT, or 'state' has dropped out of its flush_model() list -- "
            "the query then reads a stale state and flags the entry anyway.",
        )
        self.assertEqual(
            overflowing.state,
            "conflict",
            "The entry that caused the day to exceed 24h must be flagged. This "
            "pins the other half of that query: the excessive_days CTE must keep "
            "summing validated hours, because 8h validated plus 20h new really is "
            "28h. Only the flagging is restricted, never the sum -- otherwise the "
            "day silently stops being over 24h and nothing is flagged at all.",
        )

    def test_validated_entry_survives_the_conflict_being_resolved(self):
        validated = self._create(duration=8.0)
        validated.action_validate()
        overflowing = self._create(duration=20.0)
        overflowing.unlink()

        self.assertEqual(
            validated.state,
            "validated",
            "Resolving an unrelated same-day conflict must not silently demote a "
            "validated work entry to draft: its payroll validation would be lost. "
            "The demotion path is asymmetric and one-directional: marking is raw "
            "SQL, resetting is an ORM domain over state not in "
            "('validated', 'cancelled'). Once marking flags a validated entry, "
            "the reset matches it and sends it to draft, and nothing sends it back.",
        )

    def test_validated_entry_without_a_type_is_not_flagged(self):
        validated = self._create()
        validated.action_validate()
        validated.with_context(hr_work_entry_no_check=True).write(
            {"work_entry_type_id": False}
        )

        validated._check_if_error()

        self.assertEqual(
            validated.state,
            "validated",
            "_check_if_error must not flag an entry payroll has already banked. "
            "Its undefined_type branch is reachable on validated records: "
            "hr_work_entry_holidays' post-init hook calls "
            "env['hr.work.entry'].search([])._check_if_error() over the whole "
            "table, and hr_payroll calls it on a payslip run's entries.",
        )

    def test_flagging_does_not_resurrect_a_cancelled_entry(self):
        cancelled = self._create(state="cancelled")
        cancelled.with_context(hr_work_entry_no_check=True).write(
            {"work_entry_type_id": False}
        )

        cancelled._check_if_error()

        self.assertEqual(
            cancelled.state,
            "cancelled",
            "A cancelled entry must not be flagged as conflicting.",
        )
        self.assertFalse(
            cancelled.active,
            "Flagging a cancelled entry would un-archive it, because active is "
            "derived from state and only 'cancelled' maps to archived. The "
            "resurrected entry then re-enters the SQL 24h cap, which sums over "
            "active = TRUE, and raises phantom conflicts on its neighbours.",
        )

    def test_reactivating_does_not_demote_a_validated_entry(self):
        validated = self._create()
        validated.action_validate()

        validated.write({"active": True})

        self.assertEqual(
            validated.state,
            "validated",
            "Writing active=True on an entry that is already active must be a "
            "no-op for state. Only a cancelled entry is resurrected to draft; "
            "mapping active=True to draft unconditionally silently discards a "
            "payslip validation.",
        )

    def test_reactivating_a_cancelled_entry_returns_it_to_draft(self):
        cancelled = self._create(state="cancelled")

        cancelled.write({"active": True})

        self.assertEqual(
            cancelled.state,
            "draft",
            "Un-archiving a cancelled entry must still return it to draft.",
        )

    def test_action_validate_skips_cancelled_entries(self):
        cancelled = self._create(state="cancelled")

        cancelled.action_validate()

        self.assertEqual(
            cancelled.state,
            "cancelled",
            "An archived entry must not be swept into a payslip by a bulk "
            "validation: action_validate excludes entries already validated, so "
            "it must exclude cancelled ones for the same reason.",
        )

    def test_create_with_cancelled_state_archives_the_entry(self):
        entry = self._create(state="cancelled")
        self.assertFalse(
            entry.active,
            "create() must keep state and active consistent the way write() does.",
        )

    def test_create_with_active_false_cancels_the_entry(self):
        entry = self._create(active=False)
        self.assertEqual(
            entry.state,
            "cancelled",
            "create() must keep state and active consistent the way write() does.",
        )

    def test_cancelled_entry_does_not_count_toward_the_daily_cap(self):
        self._create(duration=20.0, state="cancelled")
        entry = self._create(duration=8.0)
        self.assertEqual(
            entry.state,
            "draft",
            "A cancelled work entry must not contribute its duration to the 24h "
            "daily cap, otherwise it raises phantom conflicts. The cap is summed "
            "in SQL over active = TRUE, so this holds only while create() keeps "
            "state and active in step the way write() does.",
        )

    def test_amount_rate_follows_the_defaulted_work_entry_type(self):
        entry = self.env["hr.work.entry"].create(
            {
                "employee_id": self.employee.id,
                "date": date(2024, 6, 11),
                "duration": 8.0,
            }
        )
        self.assertEqual(
            entry.amount_rate,
            entry.work_entry_type_id.amount_rate,
            "amount_rate must follow the work entry type even when the type comes "
            "from the field default rather than from the create() values. A "
            "create() override cannot read work_entry_type_id from vals for this: "
            "the field default only fires inside super().create(), so the key is "
            "absent exactly when the UI omits it, and the rate silently lands 0.",
        )

    def test_amount_rate_follows_an_explicit_work_entry_type(self):
        entry = self._create()
        self.assertEqual(entry.amount_rate, 2.0)

    def test_amount_rate_can_be_overridden(self):
        entry = self._create(amount_rate=0.5)
        self.assertEqual(
            entry.amount_rate, 0.5, "An explicit amount_rate must win over the type's."
        )

    def test_display_name_follows_a_work_entry_type_rename(self):
        entry = self._create()
        self.assertEqual(entry.display_name, "Paid Attendance - 8h00")
        self.work_entry_type.name = "Renamed Attendance"
        self.assertEqual(
            entry.display_name,
            "Renamed Attendance - 8h00",
            "display_name reads work_entry_type_id.name, so it must depend on it.",
        )

    def test_display_name_without_a_work_entry_type(self):
        entry = self._create(work_entry_type_id=False)
        self.assertNotIn(
            "False",
            entry.display_name,
            "An entry with no work entry type is exactly the conflict the UI exists "
            "to resolve; its display name must not render the string 'False'.",
        )

    def test_name_is_left_empty_on_a_manually_created_entry(self):
        entry = self._create()
        self.assertFalse(
            entry.name,
            "name is the user-editable Description, not a computed label: the "
            "form gives it placeholder 'Additional Description...', the calendar "
            'hides it with invisible="not name" and the list marks it '
            'optional="hide". Auto-filling it kills the placeholder and makes '
            "every calendar event render a redundant Type: Employee line.",
        )

    def test_get_unusual_days_requires_both_bounds(self):
        days = self.env["hr.work.entry"].get_unusual_days("2024-06-01", "2024-06-30")
        self.assertEqual(len(days), 30)

    def test_already_validated_day_is_detected_across_companies(self):
        other_company = self.env["res.company"].create({"name": "Banked Co"})
        self.env.user.company_ids = [(4, other_company.id)]
        employee = (
            self.env["hr.employee"]
            .with_company(other_company)
            .create(
                {
                    "name": "Banked Employee",
                    "company_id": other_company.id,
                    "contract_date_start": "2023-01-01",
                    "date_version": "2023-01-01",
                }
            )
        )
        banked = (
            self.env["hr.work.entry"]
            .with_company(other_company)
            .create(
                {
                    "employee_id": employee.id,
                    "work_entry_type_id": self.work_entry_type.id,
                    "date": date(2024, 8, 8),
                    "duration": 8.0,
                }
            )
        )
        banked.action_validate()

        added = (
            self.env["hr.work.entry"]
            .with_company(self.env.company)
            .create(
                {
                    "employee_id": employee.id,
                    "work_entry_type_id": self.work_entry_type.id,
                    "date": date(2024, 8, 8),
                    "duration": 4.0,
                }
            )
        )

        self.assertEqual(
            added.state,
            "conflict",
            "A day already banked in a payslip must be flagged whatever company "
            "the user is acting in. Scoping the lookup to self.env.company rather "
            "than to the entries' own employees makes the check blind whenever "
            "the acting company differs from the entry's.",
        )

    def test_get_unusual_days_uses_the_employee_calendar(self):
        part_time = self.env.company.resource_calendar_id.copy(
            {"name": "Mon-Wed", "company_id": self.company.id}
        )
        part_time.attendance_ids.filtered(lambda a: a.dayofweek in ("3", "4")).unlink()
        employee = self.env["hr.employee"].create(
            {
                "name": "Part Timer",
                "company_id": self.company.id,
                "contract_date_start": "2023-01-01",
                "date_version": "2023-01-01",
                "resource_calendar_id": part_time.id,
            }
        )

        days = (
            self.env["hr.work.entry"]
            .with_context(default_employee_id=employee.id)
            .get_unusual_days("2024-06-03", "2024-06-07")
        )

        self.assertTrue(
            days["2024-06-06"] and days["2024-06-07"],
            "The work entry calendar is always scoped to one employee via "
            "default_employee_id, so it must shade that employee's own schedule. "
            "Shading the company calendar instead shows a Mon-Wed part-timer "
            "Thursday and Friday as ordinary working days.",
        )
        self.assertFalse(
            days["2024-06-03"],
            "A day the employee does work must not be marked unusual.",
        )

    def test_get_unusual_days_ignores_another_company_global_leave(self):
        other_company = self.env["res.company"].create({"name": "Unrelated Co"})
        self.env["resource.schedule.exception"].with_company(other_company).create(
            {
                "name": "Other company shutdown",
                "date_from": "2024-06-05 00:00:00",
                "date_to": "2024-06-05 23:59:59",
            }
        )
        days = self.env["hr.work.entry"].get_unusual_days("2024-06-03", "2024-06-07")
        self.assertFalse(
            days["2024-06-05"],
            "A global time off belonging to another company must not mark a working "
            "day as unusual.",
        )
