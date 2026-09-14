import psycopg
from lxml import etree

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("-at_install", "post_install")
class TestHourlyCost(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.officer_employees = cls.env["hr.employee"].with_user(
            cls.res_users_hr_officer
        )
        cls.plain_user = mail_new_test_user(
            cls.env,
            email="plain@example.com",
            login="plain",
            groups="base.group_user",
            name="Plain User",
        )

    def test_unset_hourly_cost_reads_zero_in_the_company_currency(self):
        employee = self.officer_employees.create({"name": "Unset"})
        self.assertEqual(employee.hourly_cost, 0.0)
        self.assertEqual(employee.currency_id, employee.company_id.currency_id)

    def test_hourly_cost_rounds_to_the_currency(self):
        employee = self.officer_employees.create(
            {"name": "Rounded", "hourly_cost": 24.0385}
        )
        employee.invalidate_recordset()
        self.assertEqual(employee.hourly_cost, 24.04)

    @mute_logger("odoo.db.cursor", "odoo.sql_db")
    def test_a_negative_hourly_cost_is_refused_on_create(self):
        with self.assertRaises(psycopg.errors.CheckViolation), self.env.cr.savepoint():
            self.officer_employees.create({"name": "Negative", "hourly_cost": -1.0})

    @mute_logger("odoo.db.cursor", "odoo.sql_db")
    def test_a_negative_hourly_cost_is_refused_on_write(self):
        employee = self.officer_employees.create(
            {"name": "Positive", "hourly_cost": 42.0}
        )
        self.env.flush_all()
        with self.assertRaises(psycopg.errors.CheckViolation), self.env.cr.savepoint():
            employee.hourly_cost = -1.0
            employee.flush_recordset()

    @mute_logger("odoo.db.cursor", "odoo.sql_db")
    def test_the_refusal_is_a_database_constraint_not_only_a_python_one(self):
        employee = self.env["hr.employee"].create({"name": "Raw SQL"})
        self.env.flush_all()
        with self.assertRaises(psycopg.errors.CheckViolation), self.env.cr.savepoint():
            self.env.cr.execute(
                "UPDATE hr_employee SET hourly_cost = -1 WHERE id = %s", (employee.id,)
            )

    @mute_logger("odoo.db.cursor", "odoo.sql_db")
    def test_the_refusal_reaches_the_user_as_its_own_sentence(self):
        with self.assertRaises(psycopg.errors.CheckViolation) as caught:
            with self.env.cr.savepoint():
                self.officer_employees.create({"name": "Negative", "hourly_cost": -1.0})
        self.assertEqual(
            self.env["hr.employee"]._sql_error_to_message(caught.exception),
            "The hourly cost cannot be negative.",
        )

    def test_hourly_cost_aggregates_as_an_average_not_a_sum(self):
        department = self.env["hr.department"].create({"name": "Averaged"})
        self.env["hr.employee"].create(
            [
                {
                    "name": f"Averaged {rate}",
                    "hourly_cost": rate,
                    "department_id": department.id,
                }
                for rate in (10.0, 20.0, 60.0)
            ]
        )
        description = (
            self.env["hr.employee"]._fields["hourly_cost"].get_description(self.env)
        )
        self.assertEqual(description["aggregator"], "avg")

        [group] = self.env["hr.employee"].formatted_read_group(
            [("department_id", "=", department.id)],
            ["department_id"],
            ["hourly_cost:avg"],
        )
        self.assertEqual(group["hourly_cost:avg"], 30.0)

    def test_an_unset_hourly_cost_is_stored_as_zero_not_null(self):
        employee = self.officer_employees.create({"name": "Unset column"})
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT hourly_cost FROM hr_employee WHERE id = %s", (employee.id,)
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0.0)

    def test_two_employees_with_no_cost_set_weigh_the_same_in_an_average(self):
        department = self.env["hr.department"].create({"name": "Mixed"})
        paid, unset = self.env["hr.employee"].create(
            [
                {"name": "Paid", "hourly_cost": 30.0, "department_id": department.id},
                {"name": "Unset", "department_id": department.id},
            ]
        )
        self.env.flush_all()
        [group] = self.env["hr.employee"].formatted_read_group(
            [("id", "in", (paid + unset).ids)], [], ["hourly_cost:avg"]
        )
        self.assertEqual(group["hourly_cost:avg"], 15.0)

    def _company_in(self, currency_name, rate):
        currency = self.env.ref(f"base.{currency_name}")
        currency.active = True
        company = self.env["res.company"].create(
            {"name": f"Company {currency_name}", "currency_id": currency.id}
        )
        self.env["res.currency.rate"].create(
            {
                "name": "2020-01-01",
                "currency_id": currency.id,
                "company_id": company.id,
                "rate": rate,
            }
        )
        self.env.user.company_ids = [(4, company.id)]
        return company

    def test_moving_to_a_company_on_another_currency_converts_the_hourly_cost(self):
        employee = self.officer_employees.create({"name": "Moved", "hourly_cost": 50.0})
        self.assertEqual(employee.currency_id, self.env.company.currency_id)

        company = self._company_in("EUR", 0.8)
        employee.sudo().company_id = company

        self.assertEqual(employee.currency_id, company.currency_id)
        self.assertEqual(employee.hourly_cost, 40.0)

    def test_moving_to_a_company_on_the_same_currency_leaves_the_hourly_cost_alone(
        self,
    ):
        employee = self.officer_employees.create({"name": "Same", "hourly_cost": 50.0})
        company = self.env["res.company"].create(
            {"name": "Same currency", "currency_id": self.env.company.currency_id.id}
        )
        self.env.user.company_ids = [(4, company.id)]
        employee.sudo().company_id = company
        self.assertEqual(employee.hourly_cost, 50.0)

    def test_an_explicit_hourly_cost_written_with_the_company_wins(self):
        employee = self.officer_employees.create(
            {"name": "Explicit", "hourly_cost": 50.0}
        )
        company = self._company_in("EUR", 0.8)
        employee.sudo().write({"company_id": company.id, "hourly_cost": 33.0})
        self.assertEqual(employee.hourly_cost, 33.0)

    def test_someone_who_cannot_read_the_hourly_cost_can_still_move_the_employee(self):
        employee = self.officer_employees.create(
            {"name": "Moved by manager", "hourly_cost": 50.0}
        )
        company = self._company_in("EUR", 0.8)
        mover = self.res_users_hr_manager
        mover.company_ids = [(4, company.id)]
        employee.with_user(mover).company_id = company
        self.assertEqual(employee.hourly_cost, 40.0)

    def test_only_an_hr_user_reads_the_hourly_cost(self):
        employee = self.officer_employees.create(
            {"name": "Restricted", "hourly_cost": 50.0}
        )
        with self.assertRaises(AccessError):
            employee.with_user(self.plain_user).hourly_cost
        with self.assertRaises(AccessError):
            employee.with_user(self.plain_user).write({"hourly_cost": 1.0})

    def test_the_form_carries_the_field_for_an_hr_user_and_nothing_for_anyone_else(
        self,
    ):
        form = self.env.ref("hr.view_employee_form").id
        officer_arch = etree.fromstring(
            self.officer_employees.get_view(form, "form")["arch"]
        )
        self.assertTrue(officer_arch.xpath("//field[@name='hourly_cost']"))
        self.assertEqual(
            officer_arch.xpath("//group[@name='application_group']")[0].get(
                "invisible"
            ),
            "0",
        )

        plain_arch = etree.fromstring(
            self.env["hr.employee"]
            .with_user(self.plain_user)
            .get_view(form, "form")["arch"]
        )
        self.assertFalse(plain_arch.xpath("//field[@name='hourly_cost']"))
        self.assertFalse(plain_arch.xpath("//label[@for='hourly_cost']"))

    def test_an_hr_officer_who_is_not_a_manager_still_gets_a_currency(self):
        self.assertFalse(self.res_users_hr_officer.has_group("hr.group_hr_manager"))
        arch = etree.fromstring(
            self.officer_employees.get_view(
                self.env.ref("hr.view_employee_form").id, "form"
            )["arch"]
        )
        currencies = arch.xpath("//field[@name='currency_id']")
        self.assertTrue(currencies)
        self.assertIn(
            "hourly_cost",
            [node.getparent().get("name") for node in currencies],
        )

    def test_the_list_offers_the_hourly_cost_as_an_optional_column(self):
        arch = etree.fromstring(
            self.officer_employees.get_view(
                self.env.ref("hr.view_employee_tree").id, "list"
            )["arch"]
        )
        [column] = arch.xpath("//field[@name='hourly_cost']")
        self.assertEqual(column.get("optional"), "hide")
