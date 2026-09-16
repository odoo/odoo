from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged, users

from odoo.addons.hr.tests.test_mail_activity_plan import ActivityScheduleHRCase


@tagged("mail_activity", "mail_activity_plan")
class TestActivitySchedule(ActivityScheduleHRCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan_fleet = cls.env["mail.activity.plan"].create(
            {
                "name": "Car return plan",
                "res_model": "hr.employee",
                "template_ids": [
                    Command.create(
                        {
                            "activity_type_id": cls.activity_type_todo.id,
                            "responsible_type": "fleet_manager",
                            "summary": "Car return",
                        }
                    )
                ],
            }
        )
        model = cls.env["product.product"].create(
            {
                "name": "A3",
                "type": "consu",
                "asset_kind_id": cls.env.ref("resource_asset.kind_vehicle").id,
            }
        )
        for employee in (cls.employee_1, cls.employee_2):
            cls.env["resource.asset"].create(
                {
                    "name": f"Car of {employee.name}",
                    "kind_id": cls.env.ref("resource_asset.kind_vehicle").id,
                    "product_id": model.id,
                    "operator_employee_id": employee.id,
                    "manager_id": cls.user_manager.partner_id._get_or_create_resources(
                        cls.env.company
                    ).id,
                }
            )

    @users("admin")
    def test_responsible(self):
        for employees in (self.employee_1, self.employee_1 + self.employee_2):
            employees = employees.with_env(self.env)
            form = self._instantiate_activity_schedule_wizard(employees)
            form.plan_id = self.plan_fleet

            schedule_lines = form.plan_schedule_line_ids._records
            self.assertEqual(len(schedule_lines), 1)
            self.assertEqual(schedule_lines[0]["line_description"], "Car return")
            if len(employees) == 1:
                self.assertEqual(
                    schedule_lines[0]["responsible_user_id"], self.user_manager.id
                )
            else:
                self.assertEqual(schedule_lines[0]["responsible_user_id"], False)

            self.assertFalse(form.has_error)
            wizard = form.save()
            wizard.action_schedule_plan()
            for employee in employees:
                activities = self.get_last_activities(employee, 1)
                self.assertEqual(len(activities), 1)
                self.assertEqual(activities[0].user_id, self.user_manager)

        employees = (self.employee_1 + self.employee_2).with_env(self.env)
        self.employee_1.car_ids[0].manager_id = False
        form = self._instantiate_activity_schedule_wizard(employees)
        form.plan_id = self.plan_fleet
        self.assertTrue(form.has_warning)
        n_warning = form.warning.count("<li>")
        self.assertEqual(n_warning, 1)
        self.assertIn(
            f"The vehicle of employee {self.employee_1.name} is not linked to a fleet manager, assigning to you.",
            form.warning,
        )
        form.save()

        self.employee_1.car_ids.operator_id = False
        form = self._instantiate_activity_schedule_wizard(employees)
        form.plan_id = self.plan_fleet
        self.assertTrue(form.has_error)
        n_error = form.error.count("<li>")
        self.assertEqual(n_error, 1)
        self.assertIn(
            f"Employee {self.employee_1.name} is not linked to a vehicle.", form.error
        )
        with self.assertRaises(ValidationError):
            form.save()
