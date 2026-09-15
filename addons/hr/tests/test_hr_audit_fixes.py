from datetime import UTC, date, datetime, time, timedelta

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.libs.datetime import timezone
from odoo.tests import tagged
from odoo.tests.common import freeze_time

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestHrAuditFixes(TestHrCommon):
    def _new_employee(self, name, **vals):
        return self.env["hr.employee"].create(
            {"name": name, "date_version": "2020-01-01", **vals}
        )

    def _add_bank_account(self, employee, acc_number):
        return self.env["res.partner.bank"].create(
            {"acc_number": acc_number, "partner_id": employee.partner_id.id}
        )

    def test_version_id_context_is_per_record(self):
        emp1 = self._new_employee("E1")
        emp2 = self._new_employee("E2")
        old_version = emp1.create_version({"date_version": "2019-01-01"})
        self.assertNotEqual(
            emp1.current_version_id, old_version, "current version is the 2020 one"
        )

        combined = (emp1 | emp2).with_context(version_id=old_version.id)
        version_by_emp = {emp.id: emp.version_id for emp in combined}

        self.assertEqual(
            version_by_emp[emp1.id],
            old_version,
            "the pinned context version wins for the employee it belongs to",
        )
        self.assertEqual(
            version_by_emp[emp2.id],
            emp2.current_version_id,
            "an unrelated employee keeps its own current version",
        )

    def test_salary_distribution_autosync_and_constraint(self):
        emp = self._new_employee("Bank Guy")
        ba1 = self._add_bank_account(emp, "BE000001")
        ba2 = self._add_bank_account(emp, "BE000002")
        emp.bank_account_ids = [(6, 0, (ba1 | ba2).ids)]

        dist = emp.salary_distribution
        self.assertEqual(set(dist), {str(ba1.id), str(ba2.id)})
        total = sum(v["amount"] for v in dist.values() if v["amount_is_percentage"])
        self.assertAlmostEqual(total, 100.0, places=4)

        with self.assertRaises(ValidationError):
            emp.salary_distribution = {
                str(ba1.id): {
                    "amount": 60.0,
                    "amount_is_percentage": True,
                    "sequence": 1,
                },
                str(ba2.id): {
                    "amount": 30.0,
                    "amount_is_percentage": True,
                    "sequence": 2,
                },
            }

    def test_primary_bank_account_and_trust_toggle(self):
        emp = self._new_employee("Primary Guy")
        ba1 = self._add_bank_account(emp, "BE000011")
        ba2 = self._add_bank_account(emp, "BE000012")
        emp.bank_account_ids = [(6, 0, (ba1 | ba2).ids)]

        primary = emp.primary_bank_account_id
        self.assertIn(primary, ba1 | ba2)
        min_seq_key = min(
            emp.salary_distribution,
            key=lambda k: emp.salary_distribution[k]["sequence"],
        )
        self.assertEqual(str(primary.id), min_seq_key)

        self.assertFalse(emp.is_trusted_bank_account)
        emp.action_toggle_primary_bank_account_trust()
        self.assertTrue(emp.primary_bank_account_id.allow_out_payment)
        self.assertTrue(emp.is_trusted_bank_account)

    def test_bank_salary_amount_remaining_for_unallocated_account(self):
        emp = self._new_employee("Fixed Guy")
        ba1 = self._add_bank_account(emp, "BE000021")
        ba2 = self._add_bank_account(emp, "BE000022")
        emp.bank_account_ids = [(4, ba1.id)]
        emp.salary_distribution = {
            str(ba1.id): {
                "amount": 500.0,
                "amount_is_percentage": False,
                "sequence": 1,
            },
        }

        self.assertEqual(ba1.employee_salary_amount, 500.0)
        self.assertFalse(ba1.employee_salary_amount_is_percentage)
        self.assertEqual(ba2.employee_salary_amount, 100.0)
        self.assertTrue(ba2.employee_salary_amount_is_percentage)

    def test_get_unusual_days_without_date_to(self):
        emp = self._new_employee("Calendar Guy")
        result = emp._get_unusual_days("2020-06-01 00:00:00")
        self.assertIsInstance(result, dict)

    def test_get_unusual_days_without_employee_uses_company_calendar(self):
        calendar = self.env["resource.calendar"].create(
            {
                "name": "Monday only",
                "tz": "UTC",
                "attendance_ids": [
                    fields.Command.create(
                        {
                            "name": "Monday",
                            "dayofweek": "0",
                            "hour_from": 8,
                            "hour_to": 16,
                        }
                    ),
                ],
            }
        )
        self.env.company.resource_calendar_id = calendar
        employees = self.env["hr.employee"]
        self.assertEqual(
            employees._get_unusual_days("2020-06-01 00:00:00", "2020-06-02 23:59:59"),
            {"2020-06-01": False, "2020-06-02": True},
        )
        self.assertEqual(
            employees._get_unusual_days("2020-06-01 00:00:00"),
            {"2020-06-01": False},
        )

    def test_job_title_cleared_when_job_removed(self):
        job = self.env["hr.job"].create({"name": "Developer"})
        emp = self._new_employee("Titled Guy", job_id=job.id)
        version = emp.version_id
        self.assertEqual(version.job_title, "Developer")
        self.assertFalse(version.is_custom_job_title)

        version.job_id = False
        self.assertFalse(
            version.job_title, "a non-custom title must not survive its job"
        )

    def test_job_title_custom_survives_job_removal(self):
        job = self.env["hr.job"].create({"name": "Developer"})
        emp = self._new_employee("Custom Guy", job_id=job.id)
        version = emp.version_id
        version.job_title = "Lead Engineer"
        self.assertTrue(version.is_custom_job_title)

        version.job_id = False
        self.assertEqual(version.job_title, "Lead Engineer")

    def test_employees_count_batched(self):
        emp = self._new_employee("Counted Guy")
        partner = emp.partner_id
        self.assertEqual(partner.employees_count, 1)
        other = self.env["res.company"].create({"name": "Counted Second Employer"})
        self.env["hr.employee"].create(
            {
                "name": "Counted Guy 2",
                "date_version": "2020-01-01",
                "partner_id": partner.id,
                "company_id": other.id,
            }
        )
        partner = partner.with_context(
            allowed_company_ids=[self.env.company.id, other.id]
        )
        partner.invalidate_recordset(["employees_count"])
        self.assertEqual(partner.employees_count, 2)


@tagged("post_install", "-at_install")
class TestHrAuditCoverage(TestHrCommon):
    def _new_employee(self, name, **vals):
        return self.env["hr.employee"].create(
            {"name": name, "date_version": "2020-01-01", **vals}
        )

    def test_department_manager_propagation(self):
        m1 = self._new_employee("Manager 1")
        m2 = self._new_employee("Manager 2")
        other = self._new_employee("Other Manager")
        dept = self.env["hr.department"].create({"name": "Sales", "manager_id": m1.id})

        e1 = self._new_employee("Emp 1", department_id=dept.id, parent_id=m1.id)
        e2 = self._new_employee("Emp 2", department_id=dept.id, parent_id=m1.id)
        e3 = self._new_employee("Emp 3", department_id=dept.id, parent_id=other.id)

        dept.manager_id = m2.id

        self.assertEqual(e1.parent_id, m2, "old manager's report moves to the new one")
        self.assertEqual(e2.parent_id, m2, "old manager's report moves to the new one")
        self.assertEqual(
            e3.parent_id, other, "a member reporting elsewhere is left untouched"
        )

    @freeze_time("2026-07-13")
    def test_notify_expiring_contract_and_work_permit(self):
        company = self.env.company
        today = fields.Date.from_string("2026-07-13")
        contract_notice = company.contract_expiration_notice_period
        wp_notice = company.work_permit_expiration_notice_period

        expiring = self._new_employee(
            "Expiring Contract",
            contract_date_start="2020-01-01",
            contract_date_end=fields.Date.to_string(
                today + relativedelta(days=contract_notice)
            ),
        )
        safe = self._new_employee(
            "Safe Contract",
            contract_date_start="2020-01-01",
            contract_date_end=fields.Date.to_string(
                today + relativedelta(days=contract_notice + 30)
            ),
        )
        wp_expiring = self._new_employee(
            "Expiring Permit",
            permit_no="WP-EXPIRING",
            work_permit_expiration_date=fields.Date.to_string(
                today + relativedelta(days=wp_notice)
            ),
        )

        self.env["hr.employee"].notify_expiring_contract_work_permit()

        self.assertTrue(
            expiring.activity_ids, "expiring contract gets a reminder activity"
        )
        self.assertFalse(
            safe.activity_ids, "a contract well within its term gets no reminder"
        )
        self.assertTrue(
            wp_expiring.activity_ids, "expiring work permit gets a reminder activity"
        )

    def test_verify_pin_rejects_non_digits(self):
        emp = self._new_employee("Pin Guy")
        with self.assertRaises(ValidationError):
            emp.pin = "12ab"
        emp.pin = "1234"
        self.assertEqual(emp.pin, "1234")


@tagged("post_install", "-at_install")
class TestHrAuditRound2(TestHrCommon):
    def _new_employee(self, name, **vals):
        return self.env["hr.employee"].create(
            {"name": name, "date_version": "2020-01-01", **vals}
        )

    def test_self_write_cannot_mint_trusted_bank_account(self):
        user = mail_new_test_user(
            self.env, login="plainuser", groups="base.group_user", name="Plain User"
        )
        self.env["hr.employee"].create({"name": "Plain User", "user_id": user.id})
        vendor = self.env["res.partner"].create(
            {"name": "Vendor X", "is_company": True}
        )

        self.assertNotIn(
            "bank_account_ids",
            self.env["res.users"].SELF_WRITEABLE_FIELDS,
        )

        user_self = self.env["res.users"].with_user(user).browse(user.id)
        with self.assertRaises(AccessError):
            user_self.write(
                {
                    "bank_account_ids": [
                        (
                            0,
                            0,
                            {
                                "partner_id": vendor.id,
                                "acc_number": "ATTACKER-0001",
                                "allow_out_payment": True,
                            },
                        )
                    ]
                }
            )
        self.assertFalse(
            self.env["res.partner.bank"]
            .sudo()
            .search([("acc_number", "=", "ATTACKER-0001")]),
            "no bank account should have been created",
        )

    def test_bank_account_number_masking(self):
        mask = self.env["res.partner.bank"]._mask_account_number
        self.assertEqual(mask("1234"), "****")
        self.assertEqual(mask("12345"), "*2345")
        self.assertEqual(mask("123456"), "**3456")
        self.assertEqual(mask("1234567"), "12*4567")
        self.assertEqual(mask("0011223344556677"), "00**********6677")
        for acc in ("12345", "123456", "1234567", "0011223344556677"):
            masked = mask(acc)
            self.assertEqual(len(masked), len(acc))
            self.assertNotEqual(masked, acc)

    def test_bank_account_masking_end_to_end_non_hr(self):
        emp = self._new_employee("Masked Guy")
        ba = self.env["res.partner.bank"].create(
            {"acc_number": "123456", "partner_id": emp.partner_id.id}
        )
        emp.bank_account_ids = [(4, ba.id)]
        plain = mail_new_test_user(
            self.env, login="plainreader", groups="base.group_user", name="Reader"
        )
        display = ba.with_user(plain).display_name
        self.assertNotIn("123456", display, "the full number must not be exposed")
        self.assertEqual(display, "**3456")

    def test_combine_tz_uses_correct_offset(self):
        mx = timezone("America/Mexico_City")
        dt = self.env["hr.employee"]._combine_tz(date(2026, 7, 1), time.min, mx)
        self.assertEqual(dt.utcoffset(), timedelta(hours=-6))
        self.assertIsNone(
            self.env["hr.employee"]._combine_tz(date(2026, 7, 1), time.min, None).tzinfo
        )

    def test_combine_tz_picks_the_standard_side_of_a_dst_fold(self):
        havana = timezone("America/Havana")
        dt = self.env["hr.employee"]._combine_tz(date(2026, 11, 1), time.min, havana)
        self.assertEqual(dt.utcoffset(), timedelta(hours=-5))
        fold_zero = datetime.combine(date(2026, 11, 1), time.min).replace(tzinfo=havana)
        self.assertEqual(fold_zero.utcoffset(), timedelta(hours=-4))
        self.assertEqual(
            dt.astimezone(UTC) - fold_zero.astimezone(UTC), timedelta(hours=1)
        )
        plain = self.env["hr.employee"]._combine_tz(date(2026, 7, 1), time.min, havana)
        self.assertEqual(plain.utcoffset(), timedelta(hours=-4))

    @freeze_time("2026-06-15")
    def test_leave_on_version_last_day_gets_calendar(self):
        cal1 = self.env["resource.calendar"].search([], limit=1)
        cal2 = self.env["resource.calendar"].create({"name": "R2 Cal2"})
        emp = self._new_employee("Leave Guy", resource_calendar_id=cal1.id)
        emp.create_version(
            {"date_version": "2026-01-01", "contract_date_start": "2026-01-01"}
        )
        emp.create_version(
            {"date_version": "2026-08-01", "resource_calendar_id": cal2.id}
        )
        current = emp.version_id
        self.assertEqual(str(current.date_end), "2026-07-31")

        leave = self.env["resource.schedule.exception"].create(
            {
                "name": "last day",
                "resource_id": emp.resource_id.id,
                "date_from": datetime(2026, 7, 31, 9, 0),
                "date_to": datetime(2026, 7, 31, 17, 0),
            }
        )
        leave.invalidate_recordset(["calendar_id"])
        self.assertEqual(
            leave.calendar_id,
            current.resource_calendar_id,
            "a leave on the version's last valid day must get that version's calendar",
        )

    def test_create_version_end_without_start_raises_clean_error(self):
        emp = self._new_employee("NoContract Guy")
        emp.create_version({"date_version": "2019-01-01"})
        versions_before = self.env["hr.version"].search([("employee_id", "=", emp.id)])
        self.assertFalse(emp._is_in_contract(date(2026, 3, 1)))

        with self.assertRaises(UserError):
            emp.create_version(
                {"date_version": "2026-03-01", "contract_date_end": "2026-12-31"}
            )

        self.assertFalse(
            versions_before.filtered("contract_date_end"),
            "no version should have gained a contract end date",
        )

    def test_open_ended_version_no_overflow_in_utc_negative_tz(self):
        emp = self._new_employee("MX Open Ended", tz="America/Mexico_City")
        emp.create_version(
            {"date_version": "2026-01-01", "contract_date_start": "2026-01-01"}
        )
        self.assertFalse(
            emp.version_id.date_end, "the current version must be open-ended"
        )

        utc = timezone("UTC")
        start = datetime(2026, 7, 1).replace(tzinfo=utc)
        stop = datetime(2026, 7, 31, 23, 59, 59).replace(tzinfo=utc)

        self.assertTrue(
            emp.sudo()._get_versions_with_contract_overlap_with_period(
                start.date(), stop.date()
            ),
            "open-ended version must overlap the window to exercise the bug",
        )

        emp._get_attendance_intervals(start, stop)
        emp._get_attendance_intervals(start, stop, lunch=True)
        emp._get_calendar_attendances(start, stop)
