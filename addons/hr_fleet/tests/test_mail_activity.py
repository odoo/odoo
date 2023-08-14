# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.hr.tests.test_mail_activity_plan import TestActivityScheduleHRCase
from odoo.exceptions import ValidationError


class TestActivitySchedule(TestActivityScheduleHRCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan_fleet = cls.env['mail.activity.plan'].create({
            'name': 'Car return plan',
            'res_model_ids': [Command.link(cls.model_hr_employee.id)],
            'template_ids': [Command.create({
                'activity_type_id': cls.activity_type_todo.id,
                'summary': 'Car return',
                'responsible_type': 'fleet_manager',
            })]
        })
        cls.brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Audi"})
        for employee in (cls.employee_1, cls.employee_2):
            car = cls.env["fleet.vehicle"].create({
                "model_id": cls.env["fleet.vehicle.model"].create({
                    "brand_id": cls.brand.id,
                    "name": "A3",
                }).id,
                "driver_id": employee.user_id.partner_id.id,
                "plan_to_change_car": False,
                "manager_id": cls.user_manager.id,
            })
            employee.car_ids = car

    def test_responsible(self):
        """ Check that the responsible is correctly configured. """
        for employees in (self.employee_1, self.employee_1 + self.employee_2):
            # Happy case
            form = self._instantiate_activity_schedule_wizard(employees)
            form.plan_id = self.plan_fleet
            self.assertEqual(form.plan_assignation_summary,
                             '<ul><li>To-Do - fleet_manager: Car return</li></ul>')
            self.assertFalse(form.has_error)
            wizard = form.save()
            wizard.action_schedule_plan()
            for employee in employees:
                activities = self.get_last_activities(employee, 1)
                self.assertEqual(len(activities), 1)
                self.assertEqual(activities[0].user_id, self.user_manager)

            # Cases with errors
            self.employee_1.car_ids[0].manager_id = False
            form = self._instantiate_activity_schedule_wizard(employees)
            form.plan_id = self.plan_fleet
            self.assertTrue(form.has_error)
            n_error = form.error.count('<li>')
            self.assertEqual(n_error, 1)
            self.assertIn("Employee's vehicle test_employee1 is not linked to a fleet manager.", form.error)
            with self.assertRaises(ValidationError):
                form.save()
            employee_1_car = self.employee_1.car_ids
            self.employee_1.car_ids = self.env["fleet.vehicle"]
            form = self._instantiate_activity_schedule_wizard(employees)
            form.plan_id = self.plan_fleet
            self.assertTrue(form.has_error)
            n_error = form.error.count('<li>')
            self.assertEqual(n_error, 1)
            self.assertIn("Employee test_employee1 is not linked to a vehicle.", form.error)
            with self.assertRaises(ValidationError):
                form.save()
            self.employee_1.car_ids = employee_1_car
            self.employee_1.car_ids[0].manager_id = self.user_manager
