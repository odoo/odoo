from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestCurrentVersionIsContextIndependent(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.worker = cls.env["hr.employee"].create({"name": "Versioned Worker"})
        cls.env.flush_all()
        cls.first_version = cls.worker.version_ids[0]
        cls.first_version.date_version = "2020-01-01"
        cls.first_version.job_title = "Junior"
        cls.later_version = cls.worker.create_version({"date_version": "2021-01-01"})
        cls.later_version.job_title = "Senior"
        cls.env.flush_all()

    def _archive_the_later_version(self):
        self.later_version.active = False
        self.env.flush_all()
        self.env.invalidate_all()

    def test_cron_and_recompute_agree_when_a_version_is_archived(self):
        self._archive_the_later_version()

        self.worker._compute_current_version_id()
        self.env.flush_all()
        from_recompute = self.worker.current_version_id

        self.env["hr.employee"]._cron_update_current_version_id()
        self.env.flush_all()
        self.env.invalidate_all()
        from_cron = self.worker.current_version_id

        self.assertEqual(
            from_cron,
            from_recompute,
            "the cron and an ordinary recompute must store the same version",
        )
        self.assertEqual(
            from_cron,
            self.first_version,
            "an archived version is not the employee's current version",
        )

    def test_cron_does_not_leak_an_archived_version_onto_the_public_profile(self):
        self._archive_the_later_version()
        self.env["hr.employee"]._cron_update_current_version_id()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            self.worker.job_title,
            "Junior",
            "the employee delegates to current_version_id; it must not show an"
            " archived version's data",
        )

    def test_the_cron_still_reaches_archived_employees(self):
        self.worker.action_archive()
        self.env.flush_all()
        newer = self.worker.create_version({"date_version": "2022-01-01"})
        self.env.flush_all()
        self.env.invalidate_all()

        self.env["hr.employee"]._cron_update_current_version_id()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            self.worker.with_context(active_test=False).current_version_id,
            newer,
            "an archived employee's current version must still be refreshed",
        )


@tagged("post_install", "-at_install")
class TestLoadSampleDataButton(TestHrCommon):
    def _scenario_record_count(self):
        return self.env["ir.model.data"].search_count(
            [
                ("module", "=", "hr"),
                (
                    "name",
                    "in",
                    ["employee_category_demo", "employee_sj", "employee_eg"],
                ),
            ]
        )

    def _ensure_dep_rd_exists(self):
        if self.env.ref("hr.dep_rd", raise_if_not_found=False):
            return
        department = self.env["hr.department"].create({"name": "R&D"})
        self.env["ir.model.data"].create(
            {
                "module": "hr",
                "name": "dep_rd",
                "model": "hr.department",
                "res_id": department.id,
            }
        )

    def test_the_guard_is_not_satisfied_by_the_modules_demo_data(self):
        self._ensure_dep_rd_exists()
        self.env.flush_all()
        self.env["hr.employee"]._load_demo_data()
        self.env.flush_all()
        self.assertTrue(
            self._scenario_record_count(),
            "the button must load the scenario even when hr.dep_rd already"
            " exists from demo/hr_demo.xml",
        )

    def test_loading_twice_is_idempotent(self):
        Employee = self.env["hr.employee"]
        Employee._load_demo_data()
        self.env.flush_all()
        after_first = self._scenario_record_count()
        Employee._load_demo_data()
        self.env.flush_all()
        self.assertEqual(self._scenario_record_count(), after_first)

    def test_it_still_returns_the_reload_action(self):
        self.assertEqual(
            self.env["hr.employee"]._load_demo_data(),
            {"type": "ir.actions.client", "tag": "reload"},
        )


@tagged("post_install", "-at_install")
class TestCreateAndWriteLeaveTheCallersValuesAlone(TestHrCommon):
    def test_create_does_not_mutate_vals_list(self):
        user = mail_new_test_user(
            self.env, login="untouched_c", groups="base.group_user", name="Untouched C"
        )
        vals = {"name": "Callers Values", "user_id": user.id}
        pristine = dict(vals)
        self.env["hr.employee"].create([vals])
        self.assertEqual(vals, pristine)

    def test_a_reused_vals_dict_does_not_carry_the_first_employees_resource(self):
        Employee = self.env["hr.employee"]
        vals = {"name": "First"}
        first = Employee.create(vals)
        vals["name"] = "Second"
        second = Employee.create(vals)
        self.env.flush_all()
        self.assertNotEqual(
            first.resource_id,
            second.resource_id,
            "the second employee inherited the first one's resource through the"
            " reused dict",
        )

    def test_write_does_not_mutate_vals(self):
        user = mail_new_test_user(
            self.env, login="untouched_w", groups="base.group_user", name="Untouched W"
        )
        employee = self.env["hr.employee"].create({"name": "Written"})
        vals = {"user_id": user.id}
        pristine = dict(vals)
        employee.write(vals)
        self.assertEqual(vals, pristine)


@tagged("post_install", "-at_install")
class TestBankAccountEmployeeComputeAgreesWithSearch(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.staffer = cls.env["hr.employee"].create({"name": "Bank Owner"})
        cls.env.flush_all()
        cls.account = cls.env["res.partner.bank"].create(
            {
                "acc_number": "BE68539007547034",
                "partner_id": cls.staffer.partner_id.id,
            }
        )
        cls.env.flush_all()

    def _search_finds_the_account(self):
        found = self.env["res.partner.bank"].search(
            [("employee_id", "=", self.staffer.id)]
        )
        return self.account in found

    def test_they_agree_with_the_flag_set(self):
        self.assertEqual(self.account.employee_id, self.staffer)
        self.assertTrue(self._search_finds_the_account())

    def test_they_agree_with_the_stored_flag_cleared(self):
        self.staffer.partner_id.employee = False
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(
            self.account.employee_id,
            self.staffer,
            "the compute must resolve through employee_ids, not the stored flag",
        )
        self.assertTrue(self._search_finds_the_account())


@tagged("post_install", "-at_install")
class TestMemberOfDepartmentSearchIsOneImplementation(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.department = cls.env["hr.department"].create({"name": "Shared Dept"})
        cls.plain_reader = mail_new_test_user(
            cls.env, login="dept_reader", groups="base.group_user", name="Dept Reader"
        )
        cls.env["hr.employee"].create(
            [
                {
                    "name": "Dept Reader",
                    "user_id": cls.plain_reader.id,
                    "department_id": cls.department.id,
                },
                {
                    "name": "HR Officer",
                    "user_id": cls.res_users_hr_officer.id,
                    "department_id": cls.department.id,
                },
                {"name": "Outsider", "department_id": False},
            ]
        )
        cls.env.flush_all()

    def test_public_search_agrees_with_its_compute(self):
        Public = self.env["hr.employee"].with_user(self.plain_reader)
        matched = Public.search([("member_of_department", "in", [True])])
        self.assertTrue(matched, "the reader's own department has members")
        for record in matched:
            self.assertTrue(record.member_of_department)

    def test_version_search_agrees_with_its_compute(self):
        Version = self.env["hr.version"].with_user(self.res_users_hr_officer)
        matched = Version.search([("member_of_department", "in", [True])])
        self.assertTrue(matched)
        for record in matched:
            self.assertTrue(record.member_of_department)

    def test_version_search_never_returns_a_contract_template(self):
        template = self.env["hr.version"].create(
            {"name": "A Contract Template", "employee_id": False}
        )
        self.env.flush_all()
        matched = (
            self.env["hr.version"]
            .with_user(self.res_users_hr_officer)
            .search([("member_of_department", "in", [True])])
        )
        self.assertNotIn(template, matched)

    def test_a_reader_with_no_department_matches_nothing(self):
        stranger = mail_new_test_user(
            self.env,
            login="no_dept",
            groups="base.group_user,hr.group_hr_user",
            name="No Dept",
        )
        for model in ("hr.employee", "hr.version"):
            with self.subTest(model=model):
                self.assertFalse(
                    self.env[model]
                    .with_user(stranger)
                    .search([("member_of_department", "in", [True])]),
                    "a reader with no department is a member of none",
                )


@tagged("post_install", "-at_install")
class TestRelatedContactsAction(TestHrCommon):
    def test_a_single_contact_opens_that_contact(self):
        employee = self.env["hr.employee"].create({"name": "One Contact"})
        self.env.flush_all()
        action = employee.action_view_related_contacts()
        self.assertEqual(action["res_id"], employee.partner_id.id)
        self.assertEqual(action["view_mode"], "form")


@tagged("post_install", "-at_install")
class TestMultipleBankAccountsFlag(TestHrCommon):
    def test_the_flag_counts_accounts(self):
        employee = self.env["hr.employee"].create({"name": "Accounts"})
        self.env.flush_all()
        partner = employee.partner_id
        self.assertFalse(employee.has_multiple_bank_accounts)
        first, second = self.env["res.partner.bank"].create(
            [
                {"acc_number": "BE68539007547035", "partner_id": partner.id},
                {"acc_number": "BE68539007547036", "partner_id": partner.id},
            ]
        )
        employee.bank_account_ids = [Command.link(first.id)]
        self.assertFalse(employee.has_multiple_bank_accounts)
        employee.bank_account_ids = [Command.link(second.id)]
        self.assertTrue(employee.has_multiple_bank_accounts)


@tagged("post_install", "-at_install")
class TestManagerDepartmentReportAccessShape(TestHrCommon):
    MODEL = "mixin.hr.manager.department.report"

    IR_RULES_THAT_DEPEND_ON_THIS_SEARCH = (
        "hr_holidays/security/hr_holidays_security.xml",
        "hr_timesheet/security/hr_timesheet_security.xml",
        "hr_skills/security/hr_skills_security.xml",
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.managed = cls.env["hr.department"].create({"name": "Managed Dept"})
        cls.managed_child = cls.env["hr.department"].create(
            {"name": "Managed Sub", "parent_id": cls.managed.id}
        )
        cls.unmanaged = cls.env["hr.department"].create({"name": "Unmanaged Dept"})
        cls.boss = mail_new_test_user(
            cls.env, login="report_boss", groups="base.group_user", name="Report Boss"
        )
        cls.boss_employee = cls.env["hr.employee"].create(
            {"name": "Report Boss", "user_id": cls.boss.id}
        )
        cls.managed.manager_id = cls.boss_employee
        cls.reportee = cls.env["hr.employee"].create(
            {"name": "Reportee", "department_id": cls.managed_child.id}
        )
        cls.stranger = cls.env["hr.employee"].create(
            {"name": "Stranger", "department_id": cls.unmanaged.id}
        )
        cls.env.flush_all()

    def _report_as_boss(self):
        return self.env[self.MODEL].with_user(self.boss)

    def test_managed_departments_resolve_to_the_departments_the_user_manages(self):
        managed_ids = tuple(self._report_as_boss()._get_managed_department_ids())
        self.assertEqual(
            set(managed_ids),
            {self.managed.id},
            "only departments whose manager_id is one of the user's own employees",
        )

    def test_managed_departments_are_usable_as_a_child_of_operand(self):
        report = self._report_as_boss()
        reached = self.env["hr.employee"].search(
            [
                (
                    "department_id",
                    "child_of",
                    tuple(report._get_managed_department_ids()),
                )
            ]
        )
        self.assertIn(
            self.reportee,
            reached,
            "child_of must reach sub-departments; _get_managed_department_ids"
            " returns a Query and every caller tuple()s it",
        )
        self.assertNotIn(self.stranger, reached)

    def test_the_search_domain_is_the_compute_domain_rooted_on_employee_id(self):
        report = self._report_as_boss()
        search_domain = report._search_has_department_manager_access("in", [True])
        managed = tuple(report._get_managed_department_ids())
        self.assertEqual(
            search_domain,
            [
                "|",
                ("employee_id.user_id", "=", self.boss.id),
                ("employee_id.department_id", "child_of", managed),
            ],
            "three ir.rule domain_force declarations resolve through this exact"
            " shape (%s); it is the compute's own domain with employee_id."
            " prefixed onto each field, and the two must stay that way"
            % ", ".join(self.IR_RULES_THAT_DEPEND_ON_THIS_SEARCH),
        )

    def test_the_search_refuses_an_operator_it_cannot_answer(self):
        self.assertIs(
            self._report_as_boss()._search_has_department_manager_access("like", "x"),
            NotImplemented,
        )

    def test_compute_and_search_select_the_same_employees(self):
        report = self._report_as_boss()
        by_compute = self.env["hr.employee"].search(
            [
                "|",
                ("user_id", "=", self.boss.id),
                (
                    "department_id",
                    "child_of",
                    tuple(report._get_managed_department_ids()),
                ),
            ]
        )
        search_domain = report._search_has_department_manager_access("in", [True])
        by_search = self.env["hr.employee"].search(
            [
                "|",
                (
                    search_domain[1][0].removeprefix("employee_id."),
                    *search_domain[1][1:],
                ),
                (
                    search_domain[2][0].removeprefix("employee_id."),
                    *search_domain[2][1:],
                ),
            ]
        )
        self.assertEqual(
            by_compute,
            by_search,
            "the two domains are rooted on different models on purpose, but they"
            " must select the same employees",
        )
        self.assertIn(self.reportee, by_compute)
        self.assertIn(self.boss_employee, by_compute)
        self.assertNotIn(self.stranger, by_compute)


@tagged("post_install", "-at_install")
class TestDepartmentCompleteNameIsNeverStale(TestHrCommon):
    def _chain(self, prefix, depth=5):
        nodes, parent = [], False
        for i in range(depth):
            nodes.append(
                self.env["hr.department"].create(
                    {"name": f"{prefix}{i}", "parent_id": parent}
                )
            )
            parent = nodes[-1].id
        self.env.flush_all()
        self.env.invalidate_all()
        return nodes

    def _stored_complete_names(self, nodes):
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT id, complete_name FROM hr_department WHERE id = ANY(%s) ORDER BY id",
            ([node.id for node in nodes],),
        )
        return dict(self.env.cr.fetchall())

    def test_renaming_a_root_updates_every_descendants_stored_value(self):
        for label, reorder in (
            ("deepest-first", lambda n: list(reversed(n))),
            ("root-first", lambda n: n),
            ("middle-first", lambda n: n[2:] + n[:2]),
        ):
            with self.subTest(read_order=label):
                nodes = self._chain(f"S_{label.replace('-', '_')}_")
                nodes[0].name = f"RENAMED_{label}"
                for node in reorder(nodes):
                    node.complete_name
                stored = self._stored_complete_names(nodes)
                stale = {
                    node_id: name
                    for node_id, name in stored.items()
                    if not name.startswith(f"RENAMED_{label}")
                }
                self.assertFalse(
                    stale,
                    "complete_name is a stored recursive compute and is this model's"
                    " _rec_name; reading descendants before ancestors must not leave"
                    " the pre-rename value in the column (see ~/Odoo/CLAUDE.md §4,"
                    " _recompute_singly). Stale rows: %s" % stale,
                )
                self.env.invalidate_all()

    def test_the_order_that_keeps_it_consistent_is_declared(self):
        self.assertEqual(
            self.env["hr.department"]._order,
            "complete_name",
            "ordering by complete_name is tree-ordered (a parent's value prefixes"
            " its children's), which is what keeps the recursive recompute"
            " ancestor-first; product.category orders the same way and does not"
            " exhibit the defect",
        )


@tagged("post_install", "-at_install")
class TestContractSyncSelectsTheMatchingContract(TestHrCommon):
    def test_get_contracts_has_no_parameter_that_silently_returns_nothing(self):
        import inspect

        signature = inspect.signature(self.env["hr.employee"]._get_contracts)
        self.assertNotIn(
            "use_latest_version",
            signature.parameters,
            "use_latest_version=False returned an empty dict for every input; a"
            " parameter whose value silently discards the result is a trap, not an"
            " API",
        )

    def test_writing_contract_dates_syncs_that_contract_only(self):
        employee = self.env["hr.employee"].create({"name": "Two Contracts"})
        self.env.flush_all()
        first = employee.version_ids[0]
        first.write(
            {
                "date_version": "2020-01-01",
                "contract_date_start": "2020-01-01",
                "contract_date_end": "2020-12-31",
            }
        )
        self.env.flush_all()
        second = employee.create_version(
            {
                "date_version": "2022-01-01",
                "contract_date_start": "2022-01-01",
                "contract_date_end": "2022-12-31",
            }
        )
        self.env.flush_all()
        first.write({"contract_date_end": "2020-06-30"})
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(str(first.contract_date_end), "2020-06-30")
        self.assertEqual(
            str(second.contract_date_end),
            "2022-12-31",
            "a write to one contract's dates must not reach a different contract's"
            " versions",
        )


@tagged("post_install", "-at_install")
class TestExpiringContractNotice(TestHrCommon):
    def test_a_contract_that_starts_today_is_still_notified(self):
        company = self.env.company
        company.contract_expiration_notice_period = 30
        employee = self.env["hr.employee"].create(
            {"name": "Starts Today", "company_id": company.id}
        )
        self.env.flush_all()
        today = self.env["hr.version"].browse().env.cr.now().date()
        employee.version_id.write(
            {
                "contract_date_start": today,
                "contract_date_end": today + relativedelta(days=5),
            }
        )
        self.env.flush_all()
        self.env["hr.employee"].notify_expiring_contract_work_permit()
        self.env.flush_all()
        scheduled = self.env["mail.activity"].search_count(
            [("res_model", "=", "hr.employee"), ("res_id", "=", employee.id)]
        )
        self.assertTrue(
            scheduled,
            "a contract that starts today has started; excluding it with a strict"
            " '<' lost the notice for a short contract created on its own start date",
        )


@tagged("post_install", "-at_install")
class TestSalaryDistributionStaysCurrencyRounded(TestHrCommon):
    def _employee_with_accounts(self, count, tag):
        employee = self.env["hr.employee"].create({"name": f"Dist {tag}"})
        self.env.flush_all()
        accounts = self.env["res.partner.bank"].create(
            [
                {
                    "acc_number": f"DIST{tag}{index:04d}",
                    "partner_id": employee.partner_id.id,
                }
                for index in range(count)
            ]
        )
        employee.bank_account_ids = [Command.set(accounts.ids)]
        self.env.flush_all()
        return employee, accounts

    def _assert_clean(self, employee, label):
        distribution = employee.salary_distribution or {}
        percentages = [
            values["amount"]
            for values in distribution.values()
            if values.get("amount_is_percentage")
        ]
        rounding = employee.currency_id.round
        unrounded = [amount for amount in percentages if amount != rounding(amount)]
        self.assertFalse(
            unrounded,
            "%s: every stored allocation must be rounded to the currency's"
            " precision. The last entry used to take the raw float remainder, so"
            " 14.26000000000002 reached the jsonb column and the user's screen."
            " Unrounded: %s" % (label, unrounded),
        )
        self.assertEqual(
            rounding(sum(percentages)),
            100.0,
            "%s: percentage allocations must total 100 (%s)" % (label, percentages),
        )

    def test_every_account_count_produces_rounded_allocations(self):
        for count in (1, 2, 3, 6, 7, 11, 12):
            with self.subTest(accounts=count):
                employee, _accounts = self._employee_with_accounts(count, f"c{count}")
                self._assert_clean(employee, f"create with {count}")

    def test_removing_an_account_redistributes_without_losing_precision(self):
        for count in (3, 7):
            with self.subTest(accounts=count):
                employee, accounts = self._employee_with_accounts(count, f"r{count}")
                employee.bank_account_ids = [Command.unlink(accounts[0].id)]
                self.env.flush_all()
                self._assert_clean(employee, f"remove one of {count}")

    def test_adding_an_account_redistributes_without_losing_precision(self):
        for count in (1, 6, 7):
            with self.subTest(accounts=count):
                employee, _accounts = self._employee_with_accounts(count, f"a{count}")
                extra = self.env["res.partner.bank"].create(
                    {
                        "acc_number": f"DISTX{count}9999",
                        "partner_id": employee.partner_id.id,
                    }
                )
                employee.bank_account_ids = [Command.link(extra.id)]
                self.env.flush_all()
                self._assert_clean(employee, f"add one to {count}")


@tagged("post_install", "-at_install")
class TestTimezoneResolutionNeverReturnsFalsy(TestHrCommon):
    def test_a_contract_template_resolves_a_real_timezone(self):
        template = self.env["hr.version"].create(
            {"name": "TZ Template", "employee_id": False}
        )
        self.env.flush_all()
        self.assertFalse(
            template.tz,
            "hr.version.tz is related='employee_id.tz', so a contract template"
            " -- which has no employee -- has none",
        )
        self.assertTrue(
            template._get_schedule_tz(),
            "_get_schedule_tz used to stop at self.tz and hand back False here; callers"
            " pass the result straight to timezone(), which cannot take it",
        )

    def test_both_spellings_agree_on_an_employee(self):
        employee = self.env["hr.employee"].create({"name": "TZ Agreement"})
        self.env.flush_all()
        self.assertEqual(
            employee._get_schedule_tz(),
            employee.version_id._get_schedule_tz(),
            "two methods of the same name resolving the same question must not diverge",
        )

    def test_the_work_zone_wins_over_the_calendar_timezone(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "TZ Calendar", "tz": "Asia/Tokyo"}
        )
        employee = self.env["hr.employee"].create({"name": "TZ Precedence"})
        self.env.flush_all()
        employee.resource_id.tz = "Europe/Brussels"
        employee.version_id.resource_calendar_id = calendar
        self.env.flush_all()
        self.assertEqual(employee._get_schedule_tz(), "Europe/Brussels")
        self.assertEqual(
            employee.version_id._get_schedule_tz(),
            "Europe/Brussels",
            "an employee works the calendar's hours in their own work zone, and"
            " hr_attendance attributes overtime days in it; both spellings must"
            " agree",
        )


@tagged("post_install", "-at_install")
class TestHistoricalCalendarResolution(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.brussels = cls.env["resource.calendar"].create(
            {"name": "Hist Brussels", "tz": "Europe/Brussels"}
        )
        cls.auckland = cls.env["resource.calendar"].create(
            {"name": "Hist Auckland", "tz": "Pacific/Auckland"}
        )

    def _employee_switching_calendar(self, tag, with_contracts):
        employee = self.env["hr.employee"].create({"name": f"Hist {tag}"})
        self.env.flush_all()
        employee.resource_id.tz = "UTC"
        first = {
            "date_version": "2020-01-01",
            "resource_calendar_id": self.brussels.id,
        }
        second = {
            "date_version": "2026-06-01",
            "resource_calendar_id": self.auckland.id,
        }
        if with_contracts:
            first |= {
                "contract_date_start": "2020-01-01",
                "contract_date_end": "2026-05-31",
            }
            second |= {"contract_date_start": "2026-06-01"}
        employee.version_ids[0].write(first)
        self.env.flush_all()
        employee.create_version(second)
        self.env.flush_all()
        self.env.invalidate_all()
        return employee

    def test_a_past_date_resolves_the_calendar_in_force_then(self):
        for with_contracts in (True, False):
            with self.subTest(contracts=with_contracts):
                employee = self._employee_switching_calendar(
                    f"c{with_contracts}", with_contracts
                )
                self.assertEqual(
                    employee._get_calendars(date(2021, 3, 1))[employee.id],
                    self.brussels,
                    "the schedule in force in 2021 was Brussels. _get_calendars"
                    " selected versions with _is_in_contract, which is False for"
                    " any version carrying no contract dates, so for an employee"
                    " with no contract data the date argument was discarded and"
                    " today's calendar came back for every historical date",
                )
                self.assertEqual(
                    employee._get_calendars(date(2026, 8, 31))[employee.id],
                    self.auckland,
                )

    def test_the_timezone_batch_is_the_work_zone_at_any_date(self):
        for with_contracts in (True, False):
            with self.subTest(contracts=with_contracts):
                employee = self._employee_switching_calendar(
                    f"t{with_contracts}", with_contracts
                )
                self.assertEqual(
                    employee._get_schedule_tz_batch(datetime(2021, 3, 1, 10, 0))[
                        employee.id
                    ],
                    "UTC",
                    "hr_attendance resolves an attendance's day through this; a"
                    " schedule change must not move the zone past days are"
                    " attributed in",
                )
                self.assertEqual(
                    employee._get_schedule_tz_batch(datetime(2026, 8, 31, 10, 0))[
                        employee.id
                    ],
                    "UTC",
                )


@tagged("post_install", "-at_install")
class TestPrivateFieldDomainIsAnAccessError(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plain_user = mail_new_test_user(
            cls.env, login="domain_probe", groups="base.group_user", name="Domain Probe"
        )
        cls.env["hr.employee"].create({"name": "Domain Target", "ssnid": "123456789"})
        cls.env.flush_all()

    def test_every_search_entry_point_raises_access_error(self):
        Employee = self.env["hr.employee"].with_user(self.plain_user)
        domain = [("ssnid", "!=", False)]
        for label, call in (
            ("search", lambda: Employee.search(domain)),
            ("search_count", lambda: Employee.search_count(domain)),
            ("search_read", lambda: Employee.search_read(domain, ["name"])),
            ("search_fetch", lambda: Employee.search_fetch(domain, ["name"])),
        ):
            with self.subTest(entry_point=label):
                with self.assertRaises(
                    AccessError,
                    msg="%s must refuse a grouped field with AccessError" % label,
                ):
                    call()

    def test_a_public_field_still_searches_normally(self):
        found = (
            self.env["hr.employee"]
            .with_user(self.plain_user)
            .search([("name", "=", "Domain Target")])
        )
        self.assertTrue(found, "the guard must not swallow legitimate searches")


@tagged("post_install", "-at_install")
class TestSelfWriteDoesNotEscalateThroughRelations(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.self_user = mail_new_test_user(
            cls.env, login="self_write", groups="base.group_user", name="Self Writer"
        )
        cls.env["hr.employee"].create(
            {"name": "Self Writer", "user_id": cls.self_user.id}
        )
        cls.existing_tag = cls.env["res.partner.tag"].create(
            {"name": "Pre-existing Tag"}
        )
        cls.env.flush_all()

    def _write_as_self(self, vals):
        self.env["res.users"].with_user(self.self_user).browse(self.self_user.id).write(
            vals
        )
        self.env.flush_all()

    def test_a_self_writable_m2m_cannot_create_a_comodel_record(self):
        before = self.env["res.partner.tag"].search_count([])
        with self.assertRaises(AccessError):
            self._write_as_self(
                {"tag_ids": [Command.create({"name": "Minted By Employee"})]}
            )
        self.env.invalidate_all()
        self.assertEqual(
            self.env["res.partner.tag"].search_count([]),
            before,
            "res.users.write elevates a self-write to superuser when every key is"
            " self-writable. base's _is_escaping_own_record is what stops that"
            " elevation for a relational command outside"
            " _RELATION_ONLY_COMMANDS (LINK/UNLINK/SET/CLEAR). hr relies on that"
            " guard and tests it nowhere else: without it, every self-writable"
            " m2m becomes a way to create comodel records under sudo",
        )

    def test_a_self_writable_m2m_cannot_modify_a_comodel_record(self):
        with self.assertRaises(AccessError):
            self._write_as_self(
                {
                    "tag_ids": [
                        Command.update(self.existing_tag.id, {"name": "ESCALATED"})
                    ]
                }
            )
        self.env.invalidate_all()
        self.assertEqual(
            self.existing_tag.name,
            "Pre-existing Tag",
            "Command.update through a self-writable m2m must not reach the"
            " comodel under sudo",
        )

    def test_a_self_writable_m2m_cannot_delete_a_comodel_record(self):
        with self.assertRaises(AccessError):
            self._write_as_self({"tag_ids": [Command.delete(self.existing_tag.id)]})
        self.env.invalidate_all()
        self.assertTrue(
            self.existing_tag.exists(),
            "Command.delete through a self-writable m2m must not unlink the"
            " comodel record under sudo",
        )

    def test_linking_an_existing_tag_to_oneself_is_refused_now(self):
        with self.assertRaises(AccessError):
            self._write_as_self({"tag_ids": [Command.link(self.existing_tag.id)]})
        self.env.invalidate_all()
        self.assertNotIn(
            self.existing_tag,
            self.self_user.employee_id.sudo().tag_ids,
            "a refused self-write must not link the tag anyway",
        )
