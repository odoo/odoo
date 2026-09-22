from datetime import datetime
from unittest.mock import patch

from psycopg.errors import CheckViolation

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import Form

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class TestCalendarSyncWritesTheResourceOnce(TestHrCommon):
    def test_an_employee_write_reaches_the_resource_through_the_version_only(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "Round 5", "company_id": self.env.company.id}
        )
        Resource = self.env.registry["resource.resource"]
        original_write = Resource.write
        calendar_writes = []

        def counting_write(resources, vals):
            if "calendar_id" in vals:
                calendar_writes.append(vals["calendar_id"])
            return original_write(resources, vals)

        with patch.object(Resource, "write", counting_write):
            self.employee.write({"resource_calendar_id": calendar.id})
        self.assertEqual(calendar_writes, [calendar.id])
        self.assertEqual(self.employee.resource_id.calendar_id, calendar)
        self.assertEqual(self.employee.version_id.resource_calendar_id, calendar)


class TestArchiveOfAMixedSelection(TestHrCommon):
    def test_an_already_archived_employee_in_the_selection_still_opens_the_wizard(
        self,
    ):
        active, archived = self.env["hr.employee"].create(
            [{"name": "Still here"}, {"name": "Already gone"}]
        )
        archived.with_context(no_wizard=True).action_archive()

        action = (active | archived).action_archive()

        self.assertFalse(active.active)
        self.assertEqual(action["res_model"], "hr.departure.wizard")
        self.assertEqual(action["context"], {"active_id": active.id})


class TestDepartureWizardForAnHrOfficer(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leaving = cls.env["hr.employee"].create(
            {"name": "Leaving", "contract_date_start": "2026-01-01"}
        )

    def _wizard(self, user):
        return (
            self.env["hr.departure.wizard"]
            .with_user(user)
            .with_context(active_ids=self.leaving.ids, employee_termination=True)
        )

    def test_an_officer_opens_the_wizard_and_registers_the_departure(self):
        Wizard = self._wizard(self.res_users_hr_officer)
        defaults = Wizard.default_get(["departure_date", "employee_ids"])
        self.assertEqual(defaults["departure_date"], fields.Date.today())

        wizard = Wizard.create(
            {"departure_reason_id": self.env.ref("hr.departure_resigned").id}
        )
        self.assertFalse(wizard.set_date_end)
        wizard.action_register_departure()

        self.assertFalse(self.leaving.active)
        self.assertEqual(
            self.leaving.sudo().departure_reason_id,
            self.env.ref("hr.departure_resigned"),
        )
        self.assertFalse(self.leaving.sudo().contract_date_end)

    def test_a_manager_still_closes_the_contract_by_default(self):
        wizard = self._wizard(self.res_users_hr_manager).create(
            {"departure_reason_id": self.env.ref("hr.departure_resigned").id}
        )
        self.assertTrue(wizard.set_date_end)
        wizard.action_register_departure()
        self.assertEqual(self.leaving.sudo().contract_date_end, wizard.departure_date)


class TestPrivateAddressOnCreate(TestHrCommon):
    def test_create_keeps_the_private_address_values(self):
        employee = self.env["hr.employee"].create(
            {
                "name": "Home",
                "private_street": "12 Rue Confidentielle",
                "private_city": "Brussels",
                "private_zip": "1000",
            }
        )
        home = employee.private_address_id
        self.assertEqual(employee.private_street, "12 Rue Confidentielle")
        self.assertEqual(home.city, "Brussels")
        self.assertEqual(home.zip, "1000")
        self.assertEqual(home.type, "private")
        self.assertEqual(home.parent_id, employee.partner_id)

    def test_a_batch_create_lands_each_address_on_its_own_employee(self):
        first, second = self.env["hr.employee"].create(
            [
                {"name": "First", "private_street": "First street"},
                {"name": "Second"},
            ]
        )
        self.assertEqual(first.private_street, "First street")
        self.assertFalse(second.private_street)
        self.assertTrue(second.private_address_id)
        self.assertNotEqual(first.private_address_id, second.private_address_id)

    def test_an_unsaved_form_creates_no_partner(self):
        user = mail_new_test_user(
            self.env, login="round5_form", groups="base.group_user", name="Draft"
        )
        Partner = self.env["res.partner"]
        before = Partner.search_count([])

        form = Form(self.env["hr.employee"])
        form.name = "Draft"
        form.user_id = user
        self.assertFalse(form.private_street)
        self.assertEqual(Partner.search_count([]), before)

        employee = form.save()
        self.assertTrue(employee.private_address_id)
        self.assertEqual(employee.private_address_id.parent_id, user.partner_id)
        self.assertEqual(Partner.search_count([]), before + 1)


class TestPrivateAddressWrittenByHr(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.officer = mail_new_test_user(
            cls.env,
            login="round5_officer",
            groups="base.group_user,hr.group_hr_user",
            name="Officer Without Contact Rights",
        )
        cls.home_employee = cls.env["hr.employee"].create({"name": "Home Owner"})

    def test_an_officer_without_contact_rights_edits_the_private_address(self):
        state = self.env.ref("base.state_us_1")
        self.home_employee.with_user(self.officer).write(
            {"private_street": "1 Officer Road", "private_state_id": state.id}
        )
        home = self.home_employee.private_address_id
        self.assertEqual(home.street, "1 Officer Road")
        self.assertEqual(home.state_id, state)

    def test_the_officer_authors_the_tracked_address_change(self):
        # The employee was created in setUpClass, and a record stays untracked until the
        # precommit hooks that follow its creation have run.
        self.env.flush_all()
        self.env.cr.precommit.run()
        self.home_employee.with_user(self.officer).write(
            {"private_street": "2 Tracked Road"}
        )
        self.env.flush_all()
        self.env.cr.precommit.run()
        self.home_employee.invalidate_recordset(["message_ids"])
        tracking = self.home_employee.message_ids.tracking_value_ids.filtered(
            lambda value: value.field_id.name == "private_street"
        )
        self.assertEqual(tracking.new_value_char, "2 Tracked Road")
        self.assertEqual(tracking.mail_message_id.author_id, self.officer.partner_id)

    def test_an_officer_without_contact_rights_creates_an_employee_with_an_address(
        self,
    ):
        employee = (
            self.env["hr.employee"]
            .with_user(self.officer)
            .create({"name": "Created By Officer", "private_city": "Ghent"})
        )
        self.assertEqual(employee.sudo().private_address_id.city, "Ghent")

    def test_an_officer_without_contact_rights_links_an_employee_to_a_user(self):
        user = mail_new_test_user(
            self.env, login="round5_linked", groups="base.group_user", name="Linked"
        )
        employee = (
            self.env["hr.employee"]
            .with_user(self.officer)
            .create({"name": "Linked Employee", "user_id": user.id})
        )
        self.assertEqual(employee.sudo().partner_id, user.partner_id)

    def test_a_plain_user_still_cannot_write_another_employees_address(self):
        user = mail_new_test_user(
            self.env, login="round5_plain", groups="base.group_user", name="Plain"
        )
        with self.assertRaises(AccessError):
            self.home_employee.with_user(user).write({"private_street": "Intruder"})
        self.assertFalse(self.home_employee.private_street)


class TestPublicProfileCreateDate(TestHrCommon):
    def test_create_date_is_the_employees_not_the_current_versions(self):
        employee = self.env["hr.employee"].create({"name": "Dated"})
        self.env.flush_all()
        hired_on = datetime(2020, 1, 2, 3, 4, 5)
        self.env.cr.execute(
            "UPDATE hr_employee SET create_date = %s WHERE id = %s",
            (hired_on, employee.id),
        )
        self.env.invalidate_all()

        self.assertEqual(employee.create_date, hired_on)
        self.assertNotEqual(employee.version_id.create_date, hired_on)


class TestSelfWritableFieldsAreRealFields(TestHrCommon):
    def test_display_name_is_not_self_writable(self):
        self.assertNotIn("display_name", self.env["res.users"].SELF_WRITEABLE_FIELDS)


class TestContractTemplateWizard(TestHrCommon):
    def test_loading_a_template_records_which_template_was_applied(self):
        template = self.env["hr.version"].create(
            {"name": "Round 5 template", "wage": 1234}
        )
        wizard = (
            self.env["hr.version.wizard"]
            .with_context(active_id=self.employee.id)
            .create({"contract_template_id": template.id})
        )
        wizard.action_load_template()
        self.assertEqual(self.employee.wage, 1234)
        self.assertEqual(self.employee.version_id.contract_template_id, template)


class TestNewEmployeeSeesItsOwnVersion(TestHrCommon):
    def test_inherited_fields_read_back_on_an_unsaved_employee(self):
        department = self.env["hr.department"].create({"name": "Round 5"})
        calendar = self.env["resource.calendar"].create(
            {"name": "Round 5", "tz": "Asia/Tokyo", "company_id": self.env.company.id}
        )
        draft = self.env["hr.employee"].new(
            {
                "name": "Draft",
                "department_id": department.id,
                "resource_calendar_id": calendar.id,
            }
        )
        self.assertTrue(draft.version_id)
        self.assertEqual(draft.department_id, department)
        self.assertEqual(draft.resource_calendar_id, calendar)
        self.assertFalse(draft.version_id.id)


class TestVersionDatesSearchAgreesWithCompute(TestHrCommon):
    def test_a_version_without_a_contract_is_found_by_its_start_date(self):
        employee = self.env["hr.employee"].create(
            {"name": "No contract", "date_version": "2026-03-01"}
        )
        version = employee.version_id
        self.assertEqual(str(version.date_start), "2026-03-01")
        self.assertFalse(version.contract_date_start)
        found = self.env["hr.version"].search([("date_start", "=", "2026-03-01")])
        self.assertIn(version, found)

    def test_the_end_date_follows_the_next_version(self):
        employee = self.env["hr.employee"].create(
            {"name": "Two versions", "date_version": "2026-01-01"}
        )
        first = employee.version_id
        self.assertFalse(first.date_end)
        employee.create_version({"date_version": "2026-06-01"})
        self.assertEqual(str(first.date_end), "2026-05-31")
        self.assertIn(
            first, self.env["hr.version"].search([("date_end", "=", "2026-05-31")])
        )


class TestFixedSalaryAllocationIsValidated(TestHrCommon):
    def _employee_with_account(self):
        employee = self.env["hr.employee"].create({"name": "Paid"})
        account = self.env["res.partner.bank.account"].create(
            {"acc_number": "R5-0001", "partner_id": employee.partner_id.id}
        )
        employee.salary_bank_account_ids = [Command.link(account.id)]
        return employee, account

    def test_a_negative_fixed_amount_is_rejected(self):
        """The refusal is the database's, so it lands at the flush.

        A fixed amount is not covered by the percentage total, which skips an
        employee with no percentage row at all -- the CHECK constraint is the
        only guard, and a constraint speaks when the rows reach storage.
        """
        employee, _account = self._employee_with_account()
        with self.assertRaises(CheckViolation), self.env.cr.savepoint():
            employee.salary_allocation_ids.write(
                {"amount": -500, "amount_is_percentage": False}
            )
            self.env.flush_all()

    def test_a_non_numeric_fixed_amount_cannot_be_stored(self):
        """The JSON could hold "abc"; a Float column cannot.

        This used to need a hand-written `isinstance(amount, (float, int))`
        check, because a jsonb value carries whatever was put in it. The
        amount is a typed column now, so the rejection is the field's rather
        than a constraint's -- which is why the exception is a ValueError and
        not a ValidationError.
        """
        employee, _account = self._employee_with_account()
        with self.assertRaises(ValueError):
            employee.salary_allocation_ids.write({"amount": "abc"})

    def test_a_fixed_amount_of_zero_or_more_is_accepted(self):
        employee, _account = self._employee_with_account()
        allocation = employee.salary_allocation_ids
        allocation.write({"amount": 0, "amount_is_percentage": False})
        allocation.write({"amount": 1500.5, "amount_is_percentage": False})


class TestBatchedCreateAttachesEveryVersion(TestHrCommon):
    def test_every_employee_owns_exactly_its_own_version(self):
        employees = self.env["hr.employee"].create(
            [{"name": f"Batch {i}", "department_id": False} for i in range(5)]
        )
        for employee in employees:
            self.assertEqual(employee.version_ids, employee.current_version_id)
            self.assertEqual(employee.version_id.employee_id, employee)
            self.assertEqual(employee.version_id.company_id, employee.company_id)

    def test_overlapping_contract_dates_are_still_rejected_at_create(self):
        employee = self.env["hr.employee"].create(
            {"name": "Overlap", "contract_date_start": "2026-01-01"}
        )
        with self.assertRaises(ValidationError):
            employee.create_version(
                {
                    "date_version": "2026-06-01",
                    "contract_date_start": "2026-03-01",
                    "contract_date_end": "2026-12-31",
                }
            )
