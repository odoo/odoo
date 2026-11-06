# -*- coding: utf-8 -*-
"""Tests for the employee vehicle book (สมุดรถพนักงาน) - T11.

Covered: the most recently used vehicle is auto-filled on a new mileage
expense, the vehicle type/plate snapshot is copied, creating an expense
refreshes the vehicle's last-used date, and the record rule hides other
employees' vehicles.
"""

from datetime import timedelta

from odoo import fields
from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestVehicleBook(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.od19_mileage_rate = 5.0
        cls.employee = cls.env["hr.employee"].create({"name": "Driver One"})
        cls.product = cls.env["product.product"].create({
            "name": "Mileage Category (vehicle test)",
            "type": "service",
            "standard_price": 0.0,
            "can_be_expensed": True,
        })
        cls.old_vehicle = cls.env["od19.employee.vehicle"].create({
            "employee_id": cls.employee.id,
            "od19_plate_number": "OLD-1111",
            "od19_last_used_date": fields.Date.today() - timedelta(days=30),
        })
        cls.new_vehicle = cls.env["od19.employee.vehicle"].create({
            "employee_id": cls.employee.id,
            "od19_plate_number": "NEW-2222",
            "od19_last_used_date": fields.Date.today(),
        })

    def _mileage_form(self):
        form = Form(self.env["hr.expense"])
        form.name = "Mileage trip"
        form.employee_id = self.employee
        form.product_id = self.product
        form.payment_mode = "own_account"
        form.od19_is_mileage = True
        form.od19_mileage_distance_km = 10.0
        return form

    def test_latest_vehicle_is_auto_filled(self):
        with self._mileage_form() as form:
            expense = form.save()
        self.assertEqual(expense.od19_mileage_vehicle_id, self.new_vehicle)

    def test_vehicle_snapshot_copied(self):
        with self._mileage_form() as form:
            form.od19_mileage_vehicle_id = self.new_vehicle
            expense = form.save()
        self.assertEqual(expense.od19_mileage_plate, "NEW-2222")

    def test_create_updates_last_used_date(self):
        target = fields.Date.today() + timedelta(days=1)
        self.env["hr.expense"].create({
            "name": "Mileage trip",
            "employee_id": self.employee.id,
            "product_id": self.product.id,
            "payment_mode": "own_account",
            "od19_is_mileage": True,
            "od19_mileage_distance_km": 10.0,
            "od19_mileage_vehicle_id": self.new_vehicle.id,
            "od19_mileage_date": target,
            "quantity": 10.0,
            "total_amount": 50.0,
        })
        self.new_vehicle.invalidate_recordset()
        self.assertEqual(self.new_vehicle.od19_last_used_date, target)

    def test_other_employee_cannot_see_my_vehicles(self):
        other_user = self.env["res.users"].create({
            "name": "Other Driver",
            "login": "od19_vehicle_other",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        other_employee = self.env["hr.employee"].create({
            "name": "Driver Two",
            "user_id": other_user.id,
        })
        other_vehicle = self.env["od19.employee.vehicle"].create({
            "employee_id": other_employee.id,
            "od19_plate_number": "OTHER-9999",
        })
        visible = self.env["od19.employee.vehicle"].with_user(
            other_user).search([])
        self.assertNotIn(self.new_vehicle, visible)
        self.assertIn(other_vehicle, visible)
