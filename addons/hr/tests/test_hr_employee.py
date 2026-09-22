from datetime import datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from psycopg.errors import NotNullViolation, UniqueViolation

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tests import Form, HttpCase, TransactionCase, new_test_user, tagged, users
from odoo.tools import mute_logger

from odoo.addons.hr.tests.common import TestHrCommon


class TestHrEmployee(TestHrCommon):
    def setUp(self):
        super().setUp()
        self.user_without_image = self.env["res.users"].create(
            {
                "name": "Marc Demo",
                "email": "mark.brown23@example.com",
                "image_1920": False,
                "login": "demo_1",
                "password": "demo_123",
            }
        )
        self.employee_without_image = self.env["hr.employee"].create(
            {"user_id": self.user_without_image.id, "image_1920": False}
        )

    def test_employee_must_have_active_version(self):
        employee = self.env["hr.employee"].create({"name": "Batman"})
        self.assertEqual(len(employee.version_ids), 1)
        employee_version = employee.version_id
        with self.assertRaises(
            ValidationError, msg="An employee should always have a version"
        ):
            employee.write({"version_ids": False})
        with self.assertRaises(
            ValidationError, msg="An employee should always have a version"
        ):
            employee_version.unlink()
        with self.assertRaises(
            ValidationError, msg="An employee should always have a version"
        ):
            employee_version.write({"employee_id": self.employee_without_image.id})
        with self.assertRaises(
            ValidationError, msg="An employee should always have an active version"
        ):
            employee_version.write({"active": False})

    def test_related_partners_count_is_per_employee(self):
        e1 = self.env["hr.employee"].create({"name": "RP One"})
        e2 = self.env["hr.employee"].create({"name": "RP Two"})
        (e1 | e2)._compute_related_partners_count()
        self.assertEqual(e1.related_partners_count, 1)
        self.assertEqual(e2.related_partners_count, 1)
        self.assertNotEqual(e1.partner_id, e2.partner_id)

    def test_user_image_is_the_employee_image(self):
        import base64
        import io

        from PIL import Image

        def _png(color):
            buf = io.BytesIO()
            Image.new("RGB", (1, 1), color).save(buf, "PNG")
            return base64.b64encode(buf.getvalue())

        img_a, img_b = _png((255, 0, 0)), _png((0, 0, 255))
        user = self.env["res.users"].create(
            {
                "name": "Img User",
                "login": "img_user",
                "email": "img.user@example.com",
                "image_1920": False,
            }
        )
        employee = self.env["hr.employee"].create(
            {"user_id": user.id, "image_1920": img_a}
        )
        self.assertEqual(user.partner_id.image_1920, employee.image_1920)
        user.write({"image_1920": img_b})
        employee.invalidate_recordset(["image_1920"])
        self.assertEqual(employee.image_1920, user.partner_id.image_1920)
        self.assertNotEqual(employee.image_1920, img_a)

    def test_employee_smart_button_multi_company(self):
        partner = self.env["res.partner"].create({"name": "Partner Test"})
        company_A = self.env["res.company"].create({"name": "company_A"})
        company_B = self.env["res.company"].create({"name": "company_B"})
        self.env["hr.employee"].create(
            {
                "name": "employee_A",
                "partner_id": partner.id,
                "company_id": company_A.id,
            }
        )
        self.env["hr.employee"].create(
            {
                "name": "employee_B",
                "partner_id": partner.id,
                "company_id": company_B.id,
            }
        )

        partner.with_company(company_A)._compute_employees_count()
        self.assertEqual(partner.employees_count, 1)
        partner.with_company(company_B)._compute_employees_count()
        self.assertEqual(partner.employees_count, 1)
        single_company_action = partner.with_company(company_B).action_view_employees()
        self.assertEqual(single_company_action.get("view_mode"), "form")
        partner.with_company(company_A).with_company(
            company_B
        )._compute_employees_count()
        self.assertEqual(partner.employees_count, 2)
        multi_company_action = (
            partner.with_company(company_A)
            .with_company(company_B)
            .action_view_employees()
        )
        self.assertEqual(multi_company_action.get("view_mode"), "kanban")

    def test_employee_linked_partner(self):
        user_partner = self.user_without_image.partner_id
        work_contact = self.employee_without_image.partner_id
        self.assertEqual(user_partner, work_contact)

    def test_employee_resource(self):
        _tz = "Pacific/Apia"
        self.res_users_hr_officer.company_id.resource_calendar_id.tz = _tz
        Employee = self.env["hr.employee"].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = "Raoul Grosbedon"
        employee_form.work_email = "raoul@example.com"
        employee = employee_form.save()
        self.assertEqual(employee.tz, _tz)

    def test_employee_timezone(self):
        schedule_zone = self.res_users_hr_officer.company_id.resource_calendar_id.tz
        self.res_users_hr_officer.tz = "Africa/Cairo"
        Employee = self.env["hr.employee"].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.user_id = self.res_users_hr_officer
        employee_form.name = "Youssef Ahmed"
        employee_form.work_email = "yoahm@example.com"
        employee = employee_form.save()

        self.assertEqual(employee.tz, schedule_zone)

        self.res_users_hr_officer.tz = "Europe/Brussels"
        self.assertEqual(employee.tz, schedule_zone)

        employee.tz = "Europe/London"
        self.assertEqual(self.res_users_hr_officer.tz, "Europe/Brussels")

        with self.assertRaises(ValidationError):
            employee.tz = False

        # A person may have no timezone; the resource then keeps its own.
        self.res_users_hr_officer.tz = False
        self.assertEqual(employee.tz, "Europe/London")

        with mute_logger("odoo.db"), self.assertRaises(NotNullViolation):
            self.res_users_hr_officer.company_id.resource_calendar_id.write(
                {"tz": None}
            )

    def test_employee_from_user(self):
        _tz = "Pacific/Apia"
        _tz2 = "America/Tijuana"
        self.res_users_hr_officer.company_id.resource_calendar_id.tz = _tz
        self.res_users_hr_officer.tz = _tz2
        Employee = self.env["hr.employee"].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = "Raoul Grosbedon"
        employee_form.work_email = "raoul@example.com"
        employee_form.user_id = self.res_users_hr_officer
        employee = employee_form.save()
        # Choosing the user makes the employee that person: the name typed
        # before is replaced by the party's, and renaming afterwards renames
        # the party.
        self.assertEqual(employee.name, self.res_users_hr_officer.name)
        self.assertEqual(employee.partner_id, self.res_users_hr_officer.partner_id)
        employee.name = "Raoul Grosbedon"
        self.assertEqual(self.res_users_hr_officer.name, "Raoul Grosbedon")
        self.assertEqual(employee.work_email, self.res_users_hr_officer.email)
        self.assertEqual(employee.tz, _tz)

    def test_employee_computed_from_user(self):
        self.res_users_hr_officer.name = "Raoul Grosbedon"
        self.res_users_hr_officer.email = "raoul@example.com"
        Employee = self.env["hr.employee"]
        employee_form = Form(Employee)
        employee_form.user_id = self.res_users_hr_officer
        self.assertEqual(employee_form.name, "Raoul Grosbedon")
        self.assertEqual(employee_form.work_email, "raoul@example.com")
        employee = employee_form.save()
        self.assertEqual(employee.name, "Raoul Grosbedon")
        self.assertEqual(employee.work_email, "raoul@example.com")

    def test_employee_from_manager_tz_no_reset(self):
        _tz = "Pacific/Apia"
        self.res_users_hr_manager.tz = False
        Employee = self.env["hr.employee"].with_user(self.res_users_hr_manager)
        employee_form = Form(Employee)
        employee_form.name = "Raoul Grosbedon"
        employee_form.work_email = "raoul@example.com"
        employee_form.tz = _tz
        employee_form.user_id = self.res_users_hr_manager
        employee = employee_form.save()
        self.assertEqual(employee.name, self.res_users_hr_manager.name)
        self.assertEqual(employee.work_email, self.res_users_hr_manager.email)
        self.assertEqual(employee.tz, _tz)

    def test_employee_has_avatar_even_if_it_has_no_image(self):
        self.assertTrue(self.employee_without_image.avatar_128)
        self.assertTrue(self.employee_without_image.avatar_256)
        self.assertTrue(self.employee_without_image.avatar_512)
        self.assertTrue(self.employee_without_image.avatar_1024)
        self.assertTrue(self.employee_without_image.avatar_1920)

    def test_a_blank_after_strip_name_does_not_crash_create(self):
        for name in ("   ", "\t", ""):
            with self.subTest(name=name):
                employee = self.env["hr.employee"].create({"name": name})
                self.env.flush_all()
                self.assertFalse(
                    employee.image_1920,
                    "no avatar can be generated from a name with no first character",
                )
                self.assertTrue(
                    employee.avatar_128, "the mixin still answers with a placeholder"
                )

    def test_the_import_path_accepts_a_blank_name(self):
        result = self.env["hr.employee"].load(["name"], [["  "]])
        self.assertFalse(
            [m for m in result["messages"] if m.get("type") == "error"],
            f"import must not fail on a padded-blank name: {result['messages']}",
        )
        self.assertTrue(result["ids"])

    def test_a_real_name_still_gets_a_generated_avatar(self):
        employee = self.env["hr.employee"].create({"name": " Real Name "})
        self.env.flush_all()
        self.assertTrue(employee.image_1920)
        self.assertEqual(
            employee.partner_id.image_1920,
            employee.image_1920,
            "the work contact keeps the bytes the employee was given",
        )

    def test_employee_has_same_avatar_as_corresponding_user(self):
        self.assertEqual(
            self.employee_without_image.avatar_1920, self.user_without_image.avatar_1920
        )

    def test_employee_member_of_department(self):
        dept, dept_sub, dept_sub_sub, dept_other, dept_parent = self.env[
            "hr.department"
        ].create(
            [
                {
                    "name": "main",
                },
                {
                    "name": "sub",
                },
                {
                    "name": "sub-sub",
                },
                {
                    "name": "other",
                },
                {
                    "name": "parent",
                },
            ]
        )
        dept_sub.parent_id = dept
        dept_sub_sub.parent_id = dept_sub
        dept.parent_id = dept_parent
        emp, emp_sub, emp_sub_sub, emp_other, emp_parent = (
            self.env["hr.employee"]
            .with_user(self.res_users_hr_officer)
            .create(
                [
                    {
                        "name": "employee",
                        "department_id": dept.id,
                    },
                    {
                        "name": "employee sub",
                        "department_id": dept_sub.id,
                    },
                    {
                        "name": "employee sub sub",
                        "department_id": dept_sub_sub.id,
                    },
                    {
                        "name": "employee other",
                        "department_id": dept_other.id,
                    },
                    {
                        "name": "employee parent",
                        "department_id": dept_parent.id,
                    },
                ]
            )
        )
        self.res_users_hr_officer.employee_id = emp
        self.assertTrue(emp.member_of_department)
        self.assertTrue(emp_sub.member_of_department)
        self.assertTrue(emp_sub_sub.member_of_department)
        self.assertFalse(emp_other.member_of_department)
        self.assertFalse(emp_parent.member_of_department)
        employees = emp + emp_sub + emp_sub_sub + emp_other + emp_parent
        self.assertEqual(
            employees.filtered_domain(
                employees.version_id._search_member_of_department("in", [True])
            ),
            emp + emp_sub + emp_sub_sub,
        )
        self.assertEqual(
            employees.filtered_domain(
                ["!"] + employees.version_id._search_member_of_department("in", [True])
            ),
            emp_other + emp_parent,
        )

    def test_employee_create_from_user(self):
        employee = self.env["hr.employee"].create({"name": "Test User 3 - employee"})
        user_1, user_2, user_3 = self.env["res.users"].create(
            [
                {
                    "name": "Test User",
                    "login": "test_user",
                    "email": "test_user@odoo.com",
                },
                {
                    "name": "Test User 2",
                    "login": "test_user_2",
                    "email": "test_user_2@odoo.com",
                    "create_employee": True,
                },
                {
                    "name": "Test User 3",
                    "login": "test_user_3",
                    "email": "test_user_3@odoo.com",
                    "create_employee_id": employee.id,
                },
            ]
        )
        self.assertFalse(user_1.employee_id)
        self.assertTrue(user_2.employee_id)
        self.assertEqual(user_3.employee_id, employee)

    def test_employee_create_from_signup(self):
        partner = self.env["res.partner"].create({"name": "test partner"})
        self.env["res.users"].signup(
            {
                "name": "Test User",
                "login": "test_user",
                "email": "test_user@odoo.com",
                "password": "test_user_password",
                "partner_id": partner.id,
            }
        )
        self.assertFalse(
            self.env["res.users"].search([("login", "=", "test_user")]).employee_id
        )

    def test_employee_update_work_contact_id(self):
        user = self.env["res.users"].create(
            {
                "name": "Test",
                "login": "test",
                "email": "test@example.com",
            }
        )
        employee_A, employee_B = self.env["hr.employee"].create(
            [
                {
                    "name": "Employee A",
                    "user_id": user.id,
                    "work_email": "employee_A@example.com",
                },
                {
                    "name": "Employee B",
                    "user_id": False,
                    "work_email": "employee_B@example.com",
                },
            ]
        )
        employee_A.user_id = False
        with mute_logger("odoo.db"), self.assertRaises(UniqueViolation):
            with self.cr.savepoint():
                employee_B.user_id = user.id
                employee_B.flush_recordset()
        employee_A.partner_id = self.env["res.partner"].create(
            {"name": "Employee A", "email": "employee_A@example.com"}
        )
        employee_B.user_id = user.id
        employee_B.work_email = "new_email@example.com"
        self.assertEqual(employee_A.work_email, "employee_A@example.com")
        self.assertEqual(employee_B.work_email, "new_email@example.com")
        self.assertNotEqual(employee_A.partner_id, user.partner_id)
        self.assertEqual(employee_B.partner_id, user.partner_id)

    def test_availability_user_infos_employee(self):
        user = self.env["res.users"].create(
            [
                {
                    "name": "Test user",
                    "login": "test",
                    "email": "test@odoo.perso",
                    "phone_ids": [
                        Command.create({"number": "+32488990011", "type": "landline"})
                    ],
                }
            ]
        )
        employee = self.env["hr.employee"].create(
            [
                {
                    "name": "Test employee",
                    "user_id": user.id,
                }
            ]
        )
        user_fields = ["email", "phone_ids", "im_status"]
        for field in user_fields:
            self.assertEqual(employee[field], user[field])

    def test_set_user_on_new_employee(self):
        test_company = self.env["res.company"].create(
            {
                "name": "Test User Company",
            }
        )
        self.env["hr.employee"].create(
            {
                "name": "Hr Officer - employee",
                "user_id": self.res_users_hr_officer.id,
                "company_id": test_company.id,
            }
        )

        self.res_users_hr_officer.write(
            {"company_ids": test_company.ids, "company_id": test_company.id}
        )

        employee_form = Form(
            self.env["hr.employee"]
            .with_user(self.res_users_hr_officer)
            .with_company(company=test_company.id)
        )
        employee_form.name = "Second employee"
        employee_form.user_id = self.res_users_hr_officer
        with (
            mute_logger("odoo.db"),
            self.assertRaises(UniqueViolation),
            self.assertRaises(ValidationError),
        ):
            employee_form.save()

        employee_2 = self.env["hr.employee"].create(
            {
                "name": "Hr 2 - employee",
                "company_id": test_company.id,
            }
        )

        employee_2_form = Form(
            employee_2.with_user(self.res_users_hr_officer).with_company(
                company=test_company.id
            )
        )
        employee_2_form.user_id = self.res_users_hr_officer
        with (
            mute_logger("odoo.db"),
            self.assertRaises(UniqueViolation),
            self.assertRaises(ValidationError),
        ):
            employee_2_form.save()

    @users("admin")
    def test_change_user_on_employee(self):
        test_other_user = self.env["res.users"].create(
            {
                "name": "Test Other User",
                "login": "test_other_user",
            }
        )
        test_other_user.partner_id.company_id = self.env.company
        test_company = self.env["res.company"].create(
            {
                "name": "Test User Company",
            }
        )
        self.env.user.write(
            {"company_ids": test_company.ids, "company_id": test_company.id}
        )
        test_user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user",
            }
        )
        test_user.partner_id.company_id = test_company
        bank_account = self.env["res.partner.bank.account"].create(
            {
                "acc_number": "1234567",
                "partner_id": test_user.partner_id.id,
            }
        )
        test_employee = self.env["hr.employee"].create(
            {
                "name": "Test User - employee",
                "user_id": test_user.id,
                "company_id": test_company.id,
                "bank_account_ids": [Command.link(bank_account.id)],
            }
        )
        with Form(test_employee) as employee_form:
            employee_form.user_id = test_other_user
        with Form(test_employee) as employee_form:
            employee_form.user_id = test_user

    def test_change_user_on_employee_keep_partner(self):
        user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user",
            }
        )
        employee = self.env["hr.employee"].create(
            {
                "name": "Test User - employee",
                "user_id": user.id,
            }
        )
        employee.user_id = None
        self.assertEqual(employee.partner_id, user.partner_id)
        self.assertFalse(employee.user_id)
        user._compute_employee_id()
        user.action_create_employee()
        self.assertEqual(
            user.employee_ids,
            employee,
            "Creating the user's employee links the one their contact already has",
        )
        self.assertEqual(employee.partner_id, user.partner_id)
        self.assertEqual(employee.user_id, user)

    def test_change_user_on_employee_multi_company(self):
        company_A = self.env["res.company"].create({"name": "company_A"})
        company_B = self.env["res.company"].create({"name": "company_B"})
        user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user",
            }
        )
        partner = user.partner_id
        employee_A = self.env["hr.employee"].create(
            {
                "name": "employee_A",
                "user_id": user.id,
                "company_id": company_A.id,
            }
        )
        employee_B = self.env["hr.employee"].create(
            {"name": "employee_B", "user_id": user.id, "company_id": company_B.id}
        )
        self.assertEqual(user.with_company(company_A).employee_id, employee_A)
        self.assertEqual(user.with_company(company_B).employee_id, employee_B)
        partner.with_company(company_A).with_company(
            company_B
        )._compute_employees_count()
        self.assertEqual(partner.employees_count, 2)
        employee_A.user_id = None
        self.assertEqual(user.with_company(company_A).employee_id.ids, [])
        self.assertEqual(user.with_company(company_B).employee_id, employee_B)
        partner.with_company(company_A).with_company(
            company_B
        )._compute_employees_count()
        self.assertEqual(partner.employees_count, 2)
        employee_A.user_id = user
        with (
            mute_logger("odoo.db"),
            self.assertRaises(UniqueViolation),
            self.assertRaises(ValidationError),
        ):
            self.env["hr.employee"].create(
                {
                    "name": "new_employee_B",
                    "user_id": user.id,
                    "company_id": company_B.id,
                }
            )
        self.assertEqual(user.with_company(company_A).employee_id, employee_A)
        self.assertEqual(user.with_company(company_B).employee_id, employee_B)
        self.assertEqual(partner.employee_ids, employee_B + employee_A)

    def test_avatar(self):
        employee_georgette = self.env["hr.employee"].create(
            {"name": "Georgette Pudubec"}
        )
        self.assertTrue(employee_georgette.image_1920)
        self.assertTrue(employee_georgette.avatar_1920)

        self.assertTrue(employee_georgette.partner_id)
        self.assertTrue(employee_georgette.partner_id.image_1920)
        self.assertTrue(employee_georgette.partner_id.avatar_1920)

        user_norbert = self.env["res.users"].create(
            {"name": "Norbert Comidofisse", "login": "Norbert6870"}
        )
        self.assertTrue(user_norbert.image_1920)
        self.assertTrue(user_norbert.avatar_1920)

        employee_norbert = self.env["hr.employee"].create(
            {"name": "Norbert Employee", "user_id": user_norbert.id}
        )
        self.assertEqual(employee_norbert.image_1920, user_norbert.image_1920)
        self.assertEqual(employee_norbert.avatar_1920, user_norbert.avatar_1920)

    def test_badge_validation(self):
        employee = self.env["hr.employee"].create({"name": "Badge Employee"})

        employee_form = Form(employee)
        employee_form.barcode = "Test@badge1"
        with self.assertRaises(ValidationError):
            employee_form.save()

        employee_form.barcode = "Testàë@badge"
        with self.assertRaises(ValidationError):
            employee_form.save()

        employee_form.barcode = "Testbadge2"
        employee_form.save()

        self.assertEqual(employee_form.barcode, "Testbadge2")

    def test_departure_wizard(self):
        employee_A, employee_B, employee_C = self.env["hr.employee"].create(
            [
                {
                    "name": f"Employee {code}",
                    "user_id": False,
                    "work_email": f"employee_{code}@example.com",
                }
                for code in ["A", "B", "C"]
            ]
        )
        archiving_employees = [employee.id for employee in (employee_A, employee_C)]

        wizard = (
            self.env["hr.departure.wizard"]
            .with_context(
                employee_termination=True,
                active_ids=archiving_employees,
            )
            .create({})
        )
        wizard.action_register_departure()

        all_employees = employee_A | employee_B | employee_C
        self.assertEqual(
            all_employees.filtered(lambda e: e.active),
            employee_B,
            "Employees should have been archived",
        )

    def test_search_hr_employee_no_access(self):
        new_user = new_test_user(self.env, "employee")
        employee = self.env["hr.employee"].create(
            {
                "name": "Test Employee",
            }
        )
        domain = Domain(
            [("name", "=", "Test Employee"), ("active", "=", True)]
        ).optimize(self.env["hr.employee"])
        with self.assertNoLogs("odoo.domains"):
            self.assertEqual(
                employee.ids,
                self.env["hr.employee"].with_user(new_user).search(domain).ids,
            )

    def test_is_flexible(self):
        employee = self.env["hr.employee"].create(
            {
                "name": "Employee",
            }
        )
        self.assertTrue(employee.resource_calendar_id)
        self.assertFalse(employee.is_flexible)
        self.assertFalse(employee.is_fully_flexible)

        employee.resource_calendar_id.flexible_hours = True
        self.assertTrue(employee.is_flexible)
        self.assertFalse(employee.is_fully_flexible)

        employee.resource_calendar_id = False
        self.assertTrue(employee.is_flexible)
        self.assertTrue(employee.is_fully_flexible)

    def test_resource_calendar_sync_with_employee_one(self):
        calendar = self.env["resource.calendar"].create(
            {
                "name": "test calendar",
                "flexible_hours": True,
            }
        )
        self.assertTrue(self.employee.resource_id)
        self.assertTrue(self.employee.resource_calendar_id)
        self.assertEqual(
            self.employee.resource_calendar_id, self.employee.resource_id.calendar_id
        )
        self.assertNotEqual(self.employee.resource_calendar_id, calendar)
        self.assertTrue(
            self.employee.resource_calendar_id, self.employee.resource_id.calendar_id
        )
        old_calendar = self.employee.resource_calendar_id
        old_version = self.employee.version_id
        old_version.date_version -= relativedelta(days=1)
        self.employee.resource_calendar_id = calendar
        self.assertEqual(self.employee.resource_id.calendar_id, calendar)
        version = self.employee.create_version(
            {
                "resource_calendar_id": old_calendar.id,
                "date_version": fields.Date.today(),
            }
        )
        self.assertEqual(self.employee.current_version_id, version)
        self.assertNotEqual(self.employee.current_version_id, old_version)
        self.assertEqual(self.employee.resource_calendar_id, old_calendar)
        self.assertEqual(self.employee.resource_id.calendar_id, old_calendar)

    def test_job_title(self):
        first_job = self.env["hr.job"].create({"name": "first job"})
        second_job = self.env["hr.job"].create({"name": "second job"})

        with Form(self.employee_without_image) as employee_form:
            employee_form.job_id = first_job
            self.assertEqual(employee_form.job_title, first_job.name)

            employee_form.job_title = "custom job title"
            self.assertEqual(first_job.name, "first job")

            first_job.name = "first job modified"
            self.assertEqual(employee_form.job_title, "custom job title")
            employee_form.save()

            employee_form.job_id = second_job
            self.assertEqual(employee_form.job_title, second_job.name)

            employee_form.job_id = first_job
            self.assertEqual(employee_form.job_title, first_job.name)

    def test_flexible_working_hours(self):
        calendar_flex = self.env["resource.calendar"].create(
            [
                {
                    "tz": "Europe/Brussels",
                    "name": "flexible hours",
                    "flexible_hours": "True",
                },
            ]
        )
        employeeA = self.env["hr.employee"].create(
            {
                "name": "Employee",
            }
        )

        days = employeeA._get_unusual_days(
            str(datetime(2025, 1, 1)), str(datetime(2025, 12, 31))
        )
        self.assertTrue(days)
        self.assertTrue(days["2025-01-04"])

        employeeA.resource_calendar_id = calendar_flex.id
        days = employeeA._get_unusual_days(
            str(datetime(2025, 1, 1)), str(datetime(2025, 12, 31))
        )
        self.assertTrue(days)
        self.assertFalse(days["2025-01-04"])

    def test_user_creation_from_employee_with_invalid_email(self):
        employee = self.env["hr.employee"].create(
            {"name": "Test Employee", "work_email": "test"}
        )

        action = employee.action_create_users()
        self.assertEqual(
            action["params"]["message"],
            f"You need to set a valid work email address for {employee.name}",
        )
        self.assertFalse(employee.user_id)

    def test_user_creation_from_employee_multi_emails(self):
        employees = self.env["hr.employee"].create(
            [
                {
                    "name": "Existing Email Employee",
                    "work_email": self.user_without_image.email,
                },
                {
                    "name": "New Employee",
                    "work_email": "newuser@example.com",
                },
                {
                    "name": "Invalid Email Employee",
                    "work_email": "invalid-email",
                },
                {
                    "name": "Without Email Employee",
                    "work_email": False,
                },
                {
                    "name": "Formatted Email Employee",
                    "work_email": f'"John Doe" <{self.user_without_image.email_normalized}>',
                },
                {
                    "name": "Multi Email Employee",
                    "work_email": '"Name1" <name@test.example.com>, "Name 2" <name2@test.example.com>',
                },
            ]
        )
        employees += self.employee_without_image
        context = {"selected_ids": employees.ids}
        confirmed_employees = (
            self.env["hr.employee"].with_context(context).browse(employees.ids)
        )
        action = confirmed_employees.action_create_users()

        params = action.get("params")
        self.assertEqual(
            params.get("message"),
            f"User already exists with the same email for Employees {employees[0].name}, {employees[4].name}",
        )
        params = params.get("next").get("params")
        self.assertEqual(
            params.get("message"),
            f"You need to set a valid work email address for {employees[2].name}, {employees[5].name}",
        )
        params = params.get("next").get("params")
        self.assertEqual(
            params.get("message"),
            f"You need to set the work email address for {employees[3].name}",
        )
        params = params.get("next").get("params")
        self.assertEqual(
            params.get("message"),
            f"User already exists for Those Employees {employees[6].name}",
        )
        params = params.get("next").get("params")
        self.assertEqual(
            params.get("message"), f"Users {employees[1].name} creation successful"
        )
        self.assertTrue(employees[1].user_id)

    def test_user_contact_phone_sync(self):
        partner = self.env["res.partner"].create({"name": "Partner Test"})
        first_company = self.env["res.company"].create({"name": "First Company"})
        first_employee = self.env["hr.employee"].create(
            {
                "name": "First Employee",
                "partner_id": partner.id,
                "company_id": first_company.id,
            }
        )
        first_employee.write(
            {
                "phone_ids": [Command.create({"number": "12345", "type": "landline"})],
                "work_email": "first_employee@test.com",
            }
        )
        self.assertEqual(first_employee.phone_ids, partner.phone_ids)
        self.assertEqual(first_employee.work_email, partner.email)
        partner.write(
            {
                "phone_ids": [Command.create({"number": "67890", "type": "landline"})],
                "email": "partner@test.com",
            }
        )
        self.assertEqual(partner.phone_ids, first_employee.phone_ids)
        self.assertEqual(partner.email, first_employee.work_email)

        second_company = self.env["res.company"].create({"name": "Second Company"})
        second_employee = self.env["hr.employee"].create(
            {
                "name": "Second Employee",
                "partner_id": partner.id,
                "company_id": second_company.id,
            }
        )
        second_employee.write(
            {
                "phone_ids": [Command.create({"number": "112233", "type": "landline"})],
                "work_email": "second_employee@test.com",
            }
        )
        # One person, one set of work channels: a second employment reads and
        # writes the same party as the first.
        self.assertEqual(second_employee.phone_ids, partner.phone_ids)
        self.assertEqual(second_employee.phone_ids, first_employee.phone_ids)
        self.assertEqual(second_employee.work_email, partner.email)
        self.assertEqual(second_employee.work_email, first_employee.work_email)
        partner.write(
            {
                "phone_ids": [Command.create({"number": "445566", "type": "landline"})],
                "email": "partner_updated@test.com",
            }
        )
        self.assertEqual(partner.phone_ids, second_employee.phone_ids)
        self.assertEqual(partner.phone_ids, first_employee.phone_ids)
        self.assertEqual(partner.email, second_employee.work_email)
        self.assertEqual(partner.email, first_employee.work_email)


class TestVersionCarriesPartyValuesUntilItsDate(TransactionCase):
    @freeze_time("2024-03-10")
    def test_a_future_version_holds_the_party_values_until_it_is_due(self):
        employee = self.env["hr.employee"].create(
            {"name": "Mover", "private_city": "Bern", "children": 1}
        )
        version = employee.create_version(
            {
                "date_version": datetime(2024, 9, 28).date(),
                "private_city": "Vevey",
                "children": 2,
            }
        )
        self.assertEqual(employee.private_city, "Bern")
        self.assertEqual(employee.children, 1)
        self.assertEqual(
            version.pending_employee_vals, {"private_city": "Vevey", "children": 2}
        )
        employee._apply_pending_version_vals()
        self.assertEqual(employee.private_city, "Bern")
        with freeze_time("2024-09-28"):
            employee._apply_pending_version_vals()
        self.assertEqual(employee.private_city, "Vevey")
        self.assertEqual(employee.children, 2)
        self.assertFalse(version.pending_employee_vals)

    @freeze_time("2024-03-10")
    def test_a_version_in_effect_writes_the_party_at_once(self):
        employee = self.env["hr.employee"].create(
            {"name": "Moved", "private_city": "Bern"}
        )
        version = employee.create_version(
            {"date_version": datetime(2024, 3, 1).date(), "private_city": "Vevey"}
        )
        self.assertEqual(employee.private_city, "Vevey")
        self.assertFalse(version.pending_employee_vals)


class TestHrEmployeeDisplayNameVisibility(TransactionCase):
    def test_a_plain_employee_reads_a_manager_through_the_public_profile(self):
        user = new_test_user(self.env, "plain_employee", groups="base.group_user")
        manager = self.env["hr.employee"].create({"name": "Manager Mario"})
        employee = self.env["hr.employee"].create(
            {"name": "Plain Peach", "user_id": user.id, "parent_id": manager.id}
        )
        self.env.flush_all()
        self.assertTrue(manager.with_user(user).has_access("read"))
        with self.assertRaises(AccessError):
            manager.with_user(user).read(["private_email"])

        [values] = employee.with_user(user).read(["parent_id"])
        self.assertEqual(values["parent_id"], (manager.id, manager.display_name))
        [res] = employee.with_user(user).web_read(
            {"parent_id": {"fields": {"display_name": {}}}}
        )
        self.assertEqual(
            res["parent_id"],
            {"id": manager.id, "display_name": manager.display_name},
        )

    def test_a_portal_user_does_not_read_an_employee_name(self):
        user = new_test_user(self.env, "portal_reader", groups="base.group_portal")
        manager = self.env["hr.employee"].create({"name": "Manager Mario"})
        self.env.flush_all()
        self.assertEqual(manager.with_user(user)._get_display_name_visible_ids(), set())


@tagged("-at_install", "post_install")
class TestHrEmployeeLinks(HttpCase):
    def test_shared_private_link_permissions(self):
        user_amy = new_test_user(
            self.env,
            name="Amy Rose",
            login="amy",
            groups="base.group_user",
        )
        employee_sonic = self.env["hr.employee"].create(
            {
                "name": "Sonic the Hedgehog",
            }
        )
        self.start_tour(
            f"/odoo/employees/{employee_sonic.id}",
            "check_employee_link_opens_the_profile",
            login=user_amy.login,
        )


@tagged("-at_install", "post_install")
class TestVersionCron(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.company_id = cls.env["res.company"].create(
            {
                "name": "Pokémon Center",
                "phone_ids": [
                    Command.create({"number": "+32404040404", "type": "landline"})
                ],
            }
        )

        with freeze_time("2020-10-07"):
            cls.employee = cls.env["hr.employee"].create(
                {
                    "name": "Charizard",
                    "phone_ids": [
                        Command.create({"number": "+32404040404", "type": "landline"})
                    ],
                    "distance_home_work": 32,
                    "distance_home_work_unit": "miles",
                }
            )

    def test_version_cron_update_no_fields(self):
        with freeze_time("2023-10-06"):
            self.employee.create_version({"date_version": "2023-10-07", "wage": 4000})

        employee_values = {}
        employee_fields = [
            field
            for field in self.env["hr.employee"]._fields
            if hasattr(self.employee, field)
        ]
        for field in employee_fields:
            employee_values[field] = self.employee[field]

        with freeze_time("2023-10-06"):
            self.env["hr.employee"]._cron_update_current_version_id()

        for field in employee_fields:
            self.assertEqual(
                employee_values[field],
                self.employee[field],
                f"""No field should change if _cron_update_current_version_id() does not change the version.
    However, the field {field} changed""",
            )

    def test_version_cron_update_fields(self):
        with freeze_time("2023-10-06"):
            self.employee.create_version({"date_version": "2023-10-07", "wage": 4000})
        current_wage = self.employee.wage
        current_version = self.employee.current_version_id
        with freeze_time("2023-10-07"):
            self.env["hr.employee"]._cron_update_current_version_id()

        self.assertNotEqual(
            current_version,
            self.employee.current_version_id,
            "current_version_id should have changed after calling _cron_update_current_version_id()",
        )
        self.assertNotEqual(
            current_wage,
            self.employee.wage,
            "wage should have changed after calling _cron_update_current_version_id()",
        )


@tagged("-at_install", "post_install")
class TestHrEmployeeWebJson(HttpCase):
    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param("web.json.enabled", True)

    def test_webjson_employees(self):
        url = "/json/1/employees"
        self.env["ir.config_parameter"].set_param("web.json.enabled", True)
        self.authenticate("admin", "admin")
        CSRF_USER_HEADERS = {
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        res = self.url_open(url, headers=CSRF_USER_HEADERS)
        self.assertEqual(res.status_code, 200)


@tagged("post_install", "-at_install")
class TestPublicBirthdayLanguage(TestHrCommon):
    """The public birthday showed an English month to every reader.

    `datetime.strftime("%d %B")` takes the month name from the locale of the
    server PROCESS, not from whoever is looking at the screen, so a Spanish user
    saw "15 March".
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("es_MX")
        cls.celebrant = cls.env["hr.employee"].create(
            {
                "name": "Birthday Haver",
                "birthday": "1990-03-15",
                "birthday_public_display": True,
            }
        )

    def _string_for(self, lang):
        employee = self.celebrant.with_context(lang=lang)
        employee.invalidate_recordset(["birthday_public_display_string"])
        return employee.birthday_public_display_string

    def test_public_birthday_string_follows_the_reader_language(self):
        self.assertEqual(self._string_for("en_US"), "15 March")
        self.assertEqual(
            self._string_for("es_MX"),
            "15 marzo",
            "the month name must come from the reader's language, not the"
            " server process locale",
        )

    def test_a_hidden_birthday_stays_hidden(self):
        """The other branch must not move."""
        self.celebrant.birthday_public_display = False
        self.celebrant.invalidate_recordset(["birthday_public_display_string"])

        self.assertEqual(self.celebrant.birthday_public_display_string, "hidden")


@tagged("post_install", "-at_install")
class TestPresenceOutOfContract(TestHrCommon):
    """Somebody whose contract has ended is neither Present nor Absent.

    Under login-based presence control the state was decided purely by whether
    the user's session was online, so a leaver whose account is still open --
    notice period, handover, an account nobody has closed yet -- kept showing up
    as Present on the employee list.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.hr_config_id.hr_presence_control_login = True

    def _online_employee(self, **version_values):
        user = self.env["res.users"].create(
            {
                "name": "Presence Subject",
                "login": f"presence_{len(self.env['res.users'].search([]))}",
            }
        )
        employee = self.env["hr.employee"].create(
            {"name": "Presence Subject", "user_id": user.id, **version_values}
        )
        self.env["mail.presence"].create(
            {
                "user_id": user.id,
                "last_presence": datetime.now(),
                "status": "online",
            }
        )
        self.env.flush_all()
        employee.invalidate_recordset(["hr_presence_state"])
        return employee

    def test_presence_state_ignores_an_employee_out_of_contract(self):
        employee = self._online_employee(
            date_version="2020-01-01",
            contract_date_start="2020-01-01",
            contract_date_end="2020-12-31",
        )
        self.assertFalse(employee.is_in_contract, "the contract has ended")

        self.assertEqual(
            employee.hr_presence_state,
            "out_of_working_hour",
            "an online session does not make a leaver Present",
        )

    def test_an_employee_under_contract_is_still_reported_present(self):
        """The control: the state must keep working for everybody else."""
        employee = self._online_employee(
            date_version="2020-01-01", contract_date_start="2020-01-01"
        )
        self.assertTrue(employee.is_in_contract)

        self.assertEqual(employee.hr_presence_state, "present")
