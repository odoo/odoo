from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from freezegun import freeze_time
from lxml import etree

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tests import tagged

from .common import TestHrCommon


@tagged("post_install", "-at_install")
class TestHrAuditRound3(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Employee = cls.env["hr.employee"]

    def test_unlink_user_on_several_employees_at_once(self):
        first = self.Employee.create({"name": "Batch A"})
        second = self.Employee.create({"name": "Batch B"})
        contacts = (first | second).partner_id
        self.assertEqual(len(contacts), 2, "each employee got its own work contact")

        (first | second).write({"user_id": False})

        self.assertFalse((first | second).user_id)
        self.assertEqual(
            (first | second).partner_id,
            contacts,
            "clearing the user must not disturb the existing work contacts",
        )

    def test_set_user_on_employees_of_different_companies(self):
        other_company = self.env["res.company"].create({"name": "Round3 Co"})
        user = self.env["res.users"].create(
            {
                "name": "Round3 User",
                "login": "round3_user",
                "company_ids": [(6, 0, [self.env.company.id, other_company.id])],
                "company_id": self.env.company.id,
            }
        )
        here = self.Employee.create({"name": "Here", "company_id": self.env.company.id})
        there = self.Employee.create({"name": "There", "company_id": other_company.id})

        (here | there).write({"user_id": user.id})

        self.assertEqual(here.user_id, user)
        self.assertEqual(there.user_id, user)

    def test_a_contact_given_a_login_links_its_employee(self):
        employee = self.Employee.create({"name": "Hired Before Login"})
        user = self.env["res.users"].create(
            {
                "name": "Hired Before Login",
                "login": "hired_before_login",
                "partner_id": employee.partner_id.id,
            }
        )
        self.assertEqual(employee.user_id, user)
        user.active = False
        self.assertEqual(employee.user_id, user)

    def test_department_subscription_covers_every_written_employee(self):
        dept_a = self.env["hr.department"].create({"name": "R3 A"})
        dept_b = self.env["hr.department"].create({"name": "R3 B"})
        user_a = self.env["res.users"].create({"name": "R3 UA", "login": "r3_ua"})
        user_b = self.env["res.users"].create({"name": "R3 UB", "login": "r3_ub"})
        emp_a = self.Employee.create(
            {"name": "R3 EA", "user_id": user_a.id, "department_id": dept_a.id}
        )
        emp_b = self.Employee.create(
            {"name": "R3 EB", "user_id": user_b.id, "department_id": dept_b.id}
        )
        channel_b = self.env["discuss.channel"].create(
            {
                "name": "R3 chan B",
                "channel_type": "channel",
                "subscription_department_ids": [(6, 0, dept_b.ids)],
            }
        )
        channel_b.channel_member_ids.filtered(
            lambda member: member.partner_id == user_b.partner_id
        ).unlink()
        self.assertNotIn(user_b.partner_id, channel_b.channel_partner_ids)

        (emp_a | emp_b).write({"department_id": dept_b.id})

        self.assertIn(
            user_b.partner_id,
            channel_b.channel_partner_ids,
            "the written department's channel must auto-subscribe its members",
        )

    def test_schedule_tz_batch_answers_the_work_zone_whatever_the_version(self):
        tokyo = self.env["resource.calendar"].create(
            {"name": "R3 Tokyo", "tz": "Asia/Tokyo"}
        )
        auckland = self.env["resource.calendar"].create(
            {"name": "R3 Auckland", "tz": "Pacific/Auckland"}
        )
        employee = self.Employee.create(
            {
                "name": "R3 Tokyo Emp",
                "tz": "Asia/Tokyo",
                "resource_calendar_id": tokyo.id,
            }
        )
        employee.version_id.write(
            {
                "date_version": date(2026, 1, 10),
                "contract_date_start": date(2026, 1, 10),
                "resource_calendar_id": tokyo.id,
            }
        )
        employee.create_version(
            {"date_version": date(2026, 1, 15), "resource_calendar_id": auckland.id}
        )
        self.env.flush_all()

        instant = datetime(2026, 1, 14, 22, 0)
        self.assertEqual(
            instant.replace(tzinfo=ZoneInfo("UTC"))
            .astimezone(ZoneInfo("Asia/Tokyo"))
            .date(),
            date(2026, 1, 15),
        )
        self.assertEqual(
            employee._get_schedule_tz_batch(instant),
            {employee.id: "Asia/Tokyo"},
        )

    def test_calendar_tz_batch_keeps_each_group_to_its_own_employees(self):
        tokyo_cal = self.env["resource.calendar"].create(
            {"name": "R3 TK", "tz": "Asia/Tokyo"}
        )
        ny_cal = self.env["resource.calendar"].create(
            {"name": "R3 NY", "tz": "America/New_York"}
        )
        tokyo_emp = self.Employee.create(
            {
                "name": "R3 TK Emp",
                "tz": "Asia/Tokyo",
                "resource_calendar_id": tokyo_cal.id,
            }
        )
        ny_emp = self.Employee.create(
            {
                "name": "R3 NY Emp",
                "tz": "America/New_York",
                "resource_calendar_id": ny_cal.id,
            }
        )
        self.env.flush_all()

        self.assertEqual(
            (tokyo_emp | ny_emp)._get_schedule_tz_batch(datetime(2026, 1, 15, 3, 0)),
            {tokyo_emp.id: "Asia/Tokyo", ny_emp.id: "America/New_York"},
        )

    def test_get_calendar_at_accepts_its_own_default(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "R3 cal", "tz": "Europe/Brussels"}
        )
        employee = self.Employee.create(
            {"name": "R3 CalAt", "resource_calendar_id": calendar.id}
        )
        self.env.flush_all()

        result = employee.resource_id._get_calendar_at(
            datetime(2026, 1, 15, 3, 0, tzinfo=ZoneInfo("UTC"))
        )
        self.assertEqual(result[employee.resource_id], calendar)

    def test_public_last_activity_matches_the_private_one(self):
        user = self.env["res.users"].create(
            {"name": "R3 Presence User", "login": "r3_presence_user"}
        )
        employee = self.Employee.create(
            {"name": "R3 Presence", "user_id": user.id, "tz": "Asia/Tokyo"}
        )
        self.env["mail.presence"].create(
            {
                "user_id": user.id,
                "last_presence": datetime.now(),
                "status": "online",
            }
        )
        self.env.flush_all()
        plain_user = self.env["res.users"].create(
            {
                "name": "R3 Presence Reader",
                "login": "r3_presence_reader",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

        self.assertTrue(employee.last_activity, "real presence, so a real date")
        as_plain_user = (
            self.env["hr.employee"].with_user(plain_user).browse(employee.id)
        )
        self.assertEqual(
            (as_plain_user.last_activity, as_plain_user.last_activity_time),
            (employee.last_activity, employee.last_activity_time),
        )

    def test_member_of_department_matches_nothing_without_a_department(self):
        user = self.env["res.users"].create(
            {
                "name": "R3 No Dept",
                "login": "r3_nodept",
                "group_ids": [(4, self.env.ref("hr.group_hr_user").id)],
            }
        )
        employee = self.Employee.create({"name": "R3 No Dept Emp", "user_id": user.id})
        self.assertFalse(employee.department_id)
        self.env.flush_all()

        Version = self.env["hr.version"].with_user(user)
        self.assertEqual(
            Domain(Version._search_member_of_department("in", [True])),
            Domain.FALSE,
        )
        self.assertFalse(
            Version.search([("member_of_department", "=", True)]),
            "no department means no member, so nothing matches",
        )

    def test_bank_account_search_by_absent_employee(self):
        partner = self.env["res.partner"].create({"name": "R3 Plain"})
        plain = self.env["res.partner.bank"].create(
            {"acc_number": "R3PLAIN0001", "partner_id": partner.id}
        )
        employee = self.Employee.create({"name": "R3 Banked"})
        banked = self.env["res.partner.bank"].create(
            {"acc_number": "R3EMP00001", "partner_id": employee.partner_id.id}
        )
        employee.bank_account_ids = [(6, 0, banked.ids)]
        self.env.flush_all()

        scope = [("id", "in", (plain | banked).ids)]
        self.assertEqual(
            self.env["res.partner.bank"].search([*scope, ("employee_id", "=", False)]),
            plain,
        )
        self.assertEqual(
            self.env["res.partner.bank"].search([*scope, ("employee_id", "!=", False)]),
            banked,
        )

    def test_bank_account_search_is_usable_by_a_non_hr_user(self):
        partner = self.env["res.partner"].create({"name": "R3 NonHR Plain"})
        plain = self.env["res.partner.bank"].create(
            {"acc_number": "R3NHR0001", "partner_id": partner.id}
        )
        employee = self.Employee.create({"name": "R3 NonHR Banked"})
        banked = self.env["res.partner.bank"].create(
            {"acc_number": "R3NHR0002", "partner_id": employee.partner_id.id}
        )
        employee.bank_account_ids = [(6, 0, banked.ids)]
        plain_user = self.env["res.users"].create(
            {
                "name": "R3 Plain User",
                "login": "r3_plain_user",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.env.flush_all()

        Bank = self.env["res.partner.bank"].with_user(plain_user)
        scope = [("id", "in", (plain | banked).ids)]
        self.assertEqual(Bank.search([*scope, ("employee_id", "=", False)]), plain)
        self.assertFalse(Bank.search([*scope, ("employee_id", "!=", False)]))
        self.assertFalse(Bank.search([*scope, ("employee_id", "=", employee.id)]))

    def test_bank_account_search_matches_its_own_compute(self):
        employee = self.Employee.create({"name": "R3 Two Accounts"})
        listed = self.env["res.partner.bank"].create(
            {"acc_number": "R3TWO0001", "partner_id": employee.partner_id.id}
        )
        unlisted = self.env["res.partner.bank"].create(
            {"acc_number": "R3TWO0002", "partner_id": employee.partner_id.id}
        )
        employee.bank_account_ids = [(6, 0, listed.ids)]
        self.env.flush_all()

        self.assertEqual(unlisted.employee_id, employee, "the compute claims it")
        self.assertEqual(
            self.env["res.partner.bank"].search(
                [
                    ("id", "in", (listed | unlisted).ids),
                    ("employee_id", "=", employee.id),
                ]
            ),
            listed | unlisted,
            "so the search must return it too",
        )

    def test_batch_user_write_does_not_wipe_avatars(self):
        with_image = self.Employee.create({"name": "R3 With Image"})
        without_image = self.Employee.create({"name": "R3 Without Image"})
        without_image.image_1920 = False
        self.env.flush_all()
        original = with_image.image_1920
        self.assertTrue(original)
        self.assertFalse(without_image.image_1920)

        (with_image | without_image).write({"user_id": False})
        self.env.flush_all()

        self.assertEqual(with_image.image_1920, original)

    def test_user_write_still_seeds_a_missing_avatar(self):
        donor = self.Employee.create({"name": "R3 Donor"})
        user = self.env["res.users"].create(
            {"name": "R3 Avatar User", "login": "r3_avatar_user"}
        )
        user.image_1920 = donor.image_1920
        employee = self.Employee.create({"name": "R3 Seeded"})
        employee.image_1920 = False
        self.env.flush_all()

        employee.write({"user_id": user.id})
        self.env.flush_all()

        self.assertEqual(employee.image_1920, user.image_1920)

    def test_preferences_view_shows_only_self_readable_fields(self):
        owner = self.env["res.users"].create(
            {
                "name": "R3 Prefs Reader",
                "login": "r3_prefs_reader",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.Employee.create({"name": "R3 Prefs Reader Emp", "user_id": owner.id})
        self.env.flush_all()

        Users = self.env["res.users"].with_user(owner)
        arch = Users.get_view(self.env.ref("hr.res_users_view_form_preferences").id)[
            "arch"
        ]
        field_names = list(
            dict.fromkeys(
                node.get("name")
                for node in etree.fromstring(arch).xpath(
                    "//field[not(ancestor::field)]"
                )
                if node.get("name")
            )
        )
        self.assertTrue(field_names, "the arch must actually contain fields")

        readable = set(Users.SELF_READABLE_FIELDS)
        self.assertFalse(
            [name for name in field_names if name not in readable],
            "preferences fields missing from SELF_READABLE_FIELDS",
        )
        as_owner = Users.browse(owner.id)
        unreadable = []
        for name in field_names:
            try:
                as_owner.read([name])
            except Exception as error:
                unreadable.append((name, type(error).__name__))
        self.assertFalse(
            unreadable, "preferences fields a user cannot read: %s" % unreadable
        )

    def test_no_bank_account_relation_is_self_writable(self):
        Users = self.env["res.users"]
        self_writable = set(Users.SELF_WRITEABLE_FIELDS)
        offenders = [
            name
            for name, field in Users._fields.items()
            if name in self_writable
            and field.relational
            and field.comodel_name == "res.partner.bank"
        ]
        self.assertFalse(
            offenders,
            "self-writable relation(s) to res.partner.bank: %s" % offenders,
        )

    def test_version_periods_rejects_an_employee_only_field(self):
        employee = self.Employee.create({"name": "R3 Periods"})
        employee.version_id.write({"contract_date_start": date(2026, 1, 1)})
        self.env.flush_all()

        self.assertIn("barcode", employee._fields)
        self.assertNotIn("barcode", self.env["hr.version"]._fields)
        with self.assertRaises(UserError):
            employee._get_version_periods(
                datetime(2026, 1, 1, tzinfo=ZoneInfo("UTC")),
                datetime(2026, 3, 1, tzinfo=ZoneInfo("UTC")),
                field_name="barcode",
            )

    def test_expiry_cron_is_idempotent(self):
        company = self.env.company
        company.work_permit_expiration_notice_period = 5
        company.contract_expiration_notice_period = 5
        today = date.today()
        employee = self.Employee.create(
            {
                "name": "R3 Expiring",
                "permit_no": "R3-WP-1",
                "work_permit_expiration_date": today + timedelta(days=5),
            }
        )
        employee.version_id.write(
            {
                "contract_date_start": today - timedelta(days=30),
                "contract_date_end": today + timedelta(days=5),
            }
        )
        self.env.flush_all()

        def activity_count():
            return self.env["mail.activity"].search_count(
                [("res_model", "=", "hr.employee"), ("res_id", "=", employee.id)]
            )

        self.Employee.notify_expiring_contract_work_permit()
        self.env.flush_all()
        after_first = activity_count()
        self.assertEqual(
            after_first, 2, "one reminder for the contract, one for the work permit"
        )

        self.Employee.notify_expiring_contract_work_permit()
        self.env.flush_all()
        self.assertEqual(activity_count(), after_first, "the second run adds nothing")

    @freeze_time("2026-07-13")
    def test_expiry_cron_still_notifies_after_missing_a_day(self):
        company = self.env.company
        company.contract_expiration_notice_period = 7
        today = date(2026, 7, 13)
        inside = self.Employee.create(
            {
                "name": "R3 Inside Window",
                "date_version": "2020-01-01",
                "contract_date_start": "2020-01-01",
                "contract_date_end": fields.Date.to_string(today + timedelta(days=3)),
            }
        )
        beyond = self.Employee.create(
            {
                "name": "R3 Beyond Window",
                "date_version": "2020-01-01",
                "contract_date_start": "2020-01-01",
                "contract_date_end": fields.Date.to_string(today + timedelta(days=30)),
            }
        )
        already_over = self.Employee.create(
            {
                "name": "R3 Already Expired",
                "date_version": "2020-01-01",
                "contract_date_start": "2020-01-01",
                "contract_date_end": fields.Date.to_string(today - timedelta(days=1)),
            }
        )
        self.env.flush_all()

        self.Employee.notify_expiring_contract_work_permit()
        self.env.flush_all()

        self.assertTrue(inside.activity_ids, "inside the window, so notified")
        self.assertFalse(beyond.activity_ids, "past the window, not yet due")
        self.assertFalse(
            already_over.activity_ids, "already expired, the window starts today"
        )

        self.Employee.notify_expiring_contract_work_permit()
        self.env.flush_all()
        self.assertEqual(len(inside.activity_ids), 1)

    def test_versions_count_follows_its_versions(self):
        employee = self.Employee.create({"name": "R3 Counting"})
        self.env.flush_all()
        self.assertEqual(employee.versions_count, 1)

        employee.create_version({"date_version": date.today() + timedelta(days=10)})
        self.env.flush_all()

        self.assertEqual(employee.versions_count, 2)

    def test_date_state_fields_stay_consistent(self):
        today = date.today()
        employee = self.Employee.create({"name": "R3 Dates"})
        employee.version_id.write(
            {
                "date_version": today - timedelta(days=10),
                "contract_date_start": today - timedelta(days=10),
            }
        )
        self.env.flush_all()

        version = employee.version_id
        self.assertTrue(version.is_current)
        self.assertFalse(version.is_past)
        self.assertFalse(version.is_future)

        version.write({"contract_date_end": today - timedelta(days=1)})
        self.env.flush_all()
        version.invalidate_recordset()
        self.assertFalse(version.is_current)
        self.assertTrue(version.is_past)
        self.assertFalse(version.is_future)

    def test_newly_hired_search_covers_a_null_hire_date(self):
        recent = self.Employee.create({"name": "R3 Recent"})
        old = self.Employee.create({"name": "R3 Old"})
        undated = self.Employee.create({"name": "R3 Undated"})
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE hr_employee SET create_date = %s WHERE id = %s",
            (datetime(2020, 1, 1), old.id),
        )
        self.env.cr.execute(
            "UPDATE hr_employee SET create_date = NULL WHERE id = %s", (undated.id,)
        )
        (recent | old | undated).invalidate_recordset()

        self.assertTrue(recent.newly_hired)
        self.assertFalse(old.newly_hired)
        self.assertFalse(undated.newly_hired)

        scope = [("id", "in", (recent | old | undated).ids)]
        self.assertEqual(
            self.Employee.search([*scope, ("newly_hired", "=", True)]), recent
        )
        self.assertEqual(
            self.Employee.search([*scope, ("newly_hired", "=", False)]),
            old | undated,
            "an employee with no hire date is not newly hired, so the negative "
            "search must return them",
        )

    def test_member_of_department_search_agrees_with_its_compute(self):
        user = self.env["res.users"].create(
            {
                "name": "R3 Public NoDept",
                "login": "r3_public_nodept",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        employee = self.Employee.create(
            {"name": "R3 Public NoDept Emp", "user_id": user.id}
        )
        self.env.flush_all()
        self.assertFalse(employee.department_id)

        Public = self.env["hr.employee"].with_user(user)
        self.assertFalse(Public.browse(employee.id).member_of_department)
        self.assertFalse(
            Public.search([("member_of_department", "=", True)]),
            "the field reads False on every row, so the filter must match none",
        )

    def test_expected_attendances_leave_domain_agrees_across_branches(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "R3 Leave Domain", "tz": "UTC"}
        )
        period_start = datetime(2026, 3, 2, tzinfo=ZoneInfo("UTC"))
        period_stop = datetime(2026, 3, 6, 23, 59, tzinfo=ZoneInfo("UTC"))
        self.env["resource.schedule.exception"].create(
            {
                "name": "R3 Public Holiday",
                "calendar_id": calendar.id,
                "date_from": datetime(2026, 3, 4, 0, 0),
                "date_to": datetime(2026, 3, 4, 23, 59),
                "time_type_id": self.env.ref("resource.time_type_work").id,
            }
        )

        without_contract = self.Employee.create(
            {"name": "R3 No Contract", "resource_calendar_id": calendar.id}
        )
        with_contract = self.Employee.create(
            {"name": "R3 In Contract", "resource_calendar_id": calendar.id}
        )
        with_contract.version_id.write(
            {
                "date_version": date(2026, 1, 1),
                "contract_date_start": date(2026, 1, 1),
                "resource_calendar_id": calendar.id,
            }
        )
        self.env.flush_all()

        def covers_the_holiday(employee):
            intervals = employee._get_expected_attendances(period_start, period_stop)
            return any(
                start.date() == date(2026, 3, 4) for start, _stop, _meta in intervals
            )

        self.assertTrue(
            covers_the_holiday(without_contract),
            'a time_type="other" entry is working time, so the no-version branch '
            "must leave the day covered; it used to subtract the entry because "
            "passing any domain to _leave_intervals_batch replaced the default "
            "time_type filter instead of narrowing it",
        )
        self.assertTrue(
            covers_the_holiday(with_contract),
            'the per-version branch filters time_type="leave" itself and always '
            "left the day covered",
        )

    def test_current_version_cron_covers_archived_employees(self):
        employee = self.Employee.create({"name": "R3 Archived"})
        employee.version_id.write({"date_version": date.today() - timedelta(days=30)})
        later = employee.create_version(
            {"date_version": date.today() - timedelta(days=1)}
        )
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE hr_employee SET current_version_id = %s WHERE id = %s",
            (employee.version_ids.sorted("date_version")[0].id, employee.id),
        )
        employee.invalidate_recordset()
        employee.action_archive()
        self.env.flush_all()
        self.assertFalse(employee.active)

        self.Employee._cron_update_current_version_id()
        self.env.flush_all()
        employee.invalidate_recordset()

        self.assertEqual(employee.current_version_id, later)

    def test_random_barcode_avoids_taken_badges(self):
        employees = self.Employee.create(
            [{"name": "R3 Badge %d" % index} for index in range(6)]
        )
        self.env.flush_all()

        employees.action_generate_random_barcode()
        self.env.flush_all()

        barcodes = employees.mapped("barcode")
        self.assertEqual(len(barcodes), len(set(barcodes)), "no duplicate in a batch")
        self.assertTrue(all(code.startswith("041") for code in barcodes))
        more = self.Employee.create([{"name": "R3 Badge more"}])
        more.action_generate_random_barcode()
        self.env.flush_all()
        self.assertNotIn(more.barcode, barcodes)

    def test_structure_type_default_resolves_for_an_hr_officer(self):
        officer_env = self.env(user=self.res_users_hr_officer)
        employee = officer_env["hr.employee"].create({"name": "R3 Officer Created"})
        self.env.flush_all()
        version = employee.sudo().version_id
        self.assertTrue(
            version.structure_type_id, "a default must have been resolved under sudo"
        )

        other_country = self.env["res.country"].search(
            [("id", "!=", self.env.company.country_id.id)], limit=1
        )
        other_company = self.env["res.company"].create(
            {"name": "R3 Other Country Co", "country_id": other_country.id}
        )
        version.sudo().write({"company_id": other_company.id})
        self.env.flush_all()
        version.with_user(self.res_users_hr_officer).invalidate_recordset()
        self.assertTrue(
            version.sudo().structure_type_id,
            "the compute must not clear the field for a non-manager",
        )

    def test_department_plan_action_domain_is_evaluated(self):
        department = self.env["hr.department"].create({"name": "R3 Plan Dept"})
        action = department.action_plan_from_department()

        self.assertIn("domain", action)
        flattened = str(action["domain"])
        self.assertIn("res_model", flattened)
        self.assertIn("department_id", flattened)
        self.env["mail.activity.plan"].search(action["domain"])

    def test_create_users_reports_a_login_clash(self):
        self.env["res.users"].create(
            {
                "name": "R3 Squatter",
                "login": "r3_taken@example.com",
                "email": "r3_other@example.com",
            }
        )
        employee = self.Employee.create({"name": "R3 Newbie"})
        employee.work_email = "r3_taken@example.com"
        self.env.flush_all()

        action = employee.action_create_users()
        self.env.flush_all()

        self.assertEqual(action["params"]["type"], "warning")
        self.assertIn("R3 Newbie", action["params"]["message"])
        self.assertFalse(employee.user_id)
