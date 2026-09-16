from odoo import fields
from odoo.tests import common


class TestHrFleetDriver(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Test Employee"})
        cls.other_employee = cls.env["hr.employee"].create({"name": "Other Employee"})
        cls.model = cls.env["product.product"].create(
            {
                "name": "A3",
                "type": "consu",
                "asset_kind_id": cls.env.ref("resource_asset.kind_vehicle").id,
            }
        )

    def _car(self, plate, **vals):
        return self.env["resource.asset"].create(
            {
                "name": plate,
                "kind_id": self.env.ref("resource_asset.kind_vehicle").id,
                "product_id": self.model.id,
                "license_plate": plate,
                **vals,
            }
        )

    def test_an_employee_drives_through_their_resource(self):
        car = self._car("HR-001", operator_employee_id=self.employee.id)
        self.assertEqual(car.operator_id, self.employee.resource_id)
        self.assertEqual(car.operator_employee_id, self.employee)
        self.assertEqual(self.employee.car_ids, car)
        self.assertEqual(self.employee.employee_cars_count, 1)
        self.assertIn("HR-001", self.employee.license_plate)
        self.assertEqual(
            self.env["hr.employee"].search([("license_plate", "ilike", "HR-001")]),
            self.employee,
        )
        self.assertEqual(
            self.env["resource.asset"].search(
                [("operator_employee_id", "=", self.employee.id)]
            ),
            car,
        )

    def test_a_future_employee_driver_takes_over(self):
        car = self._car("HR-002", operator_employee_id=self.employee.id)
        car.future_operator_employee_id = self.other_employee
        self.assertEqual(car.future_operator_id, self.other_employee.resource_id)
        car.action_accept_operator_change()
        car.invalidate_recordset()
        self.assertEqual(car.operator_employee_id, self.other_employee)
        self.assertEqual(self.employee.employee_cars_count, 1)
        self.assertFalse(self.employee.car_ids)

    def test_departure_releases_the_company_car(self):
        car = self._car("HR-003", operator_employee_id=self.employee.id)
        wizard = self.env["hr.departure.wizard"].create(
            {
                "employee_ids": [(6, 0, self.employee.ids)],
                "departure_date": fields.Date.today(),
                "release_campany_car": True,
            }
        )
        wizard._free_company_car()
        car.invalidate_recordset()
        self.assertFalse(car.operator_id)
