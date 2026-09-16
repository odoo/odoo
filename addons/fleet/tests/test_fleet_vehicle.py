from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestFleetVehicle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(
            cls.env, login="fleet_manager_probe", groups="fleet.fleet_group_manager"
        )
        cls.brand = cls.env["res.partner"].create(
            {"name": "Probe Motors", "is_manufacturer": True, "is_company": True}
        )
        cls.model = cls.env["product.product"].create(
            {
                "name": "Probe One",
                "type": "consu",
                "asset_kind_id": cls.env.ref("resource_asset.kind_vehicle").id,
                "manufacturer_id": cls.brand.id,
                "seats": 5,
                "fuel_type": "diesel",
                "co2": 120,
            }
        )
        cls.alice, cls.bob = (
            cls.env["res.partner"]
            .create([{"name": "Alice"}, {"name": "Bob"}])
            ._get_or_create_resources(cls.env["res.company"])
        )

    def _vehicle(self, plate="PRB-001", **vals):
        return (
            self.env["resource.asset"]
            .with_user(self.manager)
            .create(
                {
                    "name": f"Probe {plate}",
                    "kind_id": self.env.ref("resource_asset.kind_vehicle").id,
                    "product_id": self.model.id,
                    "license_plate": plate,
                    **vals,
                }
            )
        )

    def test_a_vehicle_is_an_asset_of_its_model(self):
        vehicle = self._vehicle()
        self.assertTrue(vehicle.is_vehicle)
        self.assertTrue(self.model.is_vehicle)
        self.assertEqual(vehicle.manufacturer_id, self.brand)
        self.assertEqual(
            (vehicle.seats, vehicle.fuel_type, vehicle.co2), (5, "diesel", 120)
        )
        self.assertEqual(vehicle.display_name, "Probe Motors / Probe One / PRB-001")
        self.assertEqual(vehicle.get_identifier("plate"), "PRB-001")
        self.assertIn(
            vehicle,
            self.env["resource.asset"].search(
                self.env.ref("fleet.fleet_vehicle_action").domain
                and [("is_vehicle", "=", True)]
            ),
        )
        self.assertFalse(
            self.env["resource.asset"]
            .create(
                {
                    "name": "Drill",
                    "kind_id": self.env.ref("resource_asset.kind_tool").id,
                }
            )
            .is_vehicle
        )

    def test_a_driver_is_an_operator_assignment(self):
        vehicle = self._vehicle()
        vehicle.operator_id = self.alice
        assignment = vehicle.assignment_ids.filtered(lambda a: a.custody_role == "operator")
        self.assertEqual(assignment.assignee_id, self.alice)
        self.assertEqual(assignment.state, "active")

        vehicle.operator_id = self.bob
        vehicle.invalidate_recordset()
        self.assertEqual(vehicle.operator_id, self.bob)
        drivers = vehicle.with_context(active_test=False).assignment_ids.filtered(
            lambda a: a.custody_role == "operator"
        )
        self.assertEqual(len(drivers), 2)
        self.assertEqual(
            drivers.filtered(lambda a: a.assignee_id == self.alice).state, "ended"
        )
        self.assertEqual(vehicle.operator_history_count, 2)
        self.assertEqual(
            self.env["resource.asset"].search([("operator_id", "=", self.bob.id)]),
            vehicle,
        )
        self.assertIn(
            "Alice",
            vehicle.message_ids.filtered(
                lambda m: (
                    m.subtype_id
                    == self.env.ref("resource_asset.mt_asset_operator_updated")
                )
            )[:1].body,
        )

    def test_a_future_driver_takes_over_when_the_change_is_applied(self):
        car = self._vehicle("PRB-CAR")
        other = self._vehicle("PRB-OLD")
        car.operator_id = self.alice
        other.operator_id = self.bob
        car.future_operator_id = self.bob
        car.invalidate_recordset()
        self.assertEqual(car.future_operator_id, self.bob)
        self.assertGreater(car.date_future_operator, fields.Datetime.now())
        self.assertEqual(
            self.env["resource.asset"].search(
                [("future_operator_id", "=", self.bob.id)]
            ),
            car,
        )

        car.action_accept_operator_change()
        (car | other).invalidate_recordset()
        self.assertEqual(car.operator_id, self.bob)
        self.assertFalse(car.future_operator_id)
        self.assertFalse(
            other.operator_id, "the new driver's previous vehicle is released"
        )

    def test_a_hand_over_date_must_be_in_the_future(self):
        vehicle = self._vehicle()
        with self.assertRaises(UserError):
            vehicle.write(
                {
                    "future_operator_id": self.alice.id,
                    "date_future_operator": fields.Datetime.now() - timedelta(days=1),
                }
            )

    def test_writing_the_odometer_records_a_reading(self):
        vehicle = self._vehicle()
        vehicle.odometer = 1200
        self.assertEqual(vehicle.odometer_meter_id.kind, "odometer")
        self.assertEqual(vehicle.odometer_meter_id.value, 1200)
        vehicle.odometer = 1500
        self.assertEqual(len(vehicle.odometer_meter_id.reading_ids), 2)
        with self.assertRaises(ValidationError):
            vehicle.odometer = 900

    def test_a_service_is_a_ledger_line(self):
        vehicle = self._vehicle()
        self.env["resource.asset.log"].create(
            {
                "asset_id": vehicle.id,
                "product_id": self.env.ref("fleet.product_product_vehicle_service").id,
                "amount": 150,
            }
        )
        self.assertEqual(vehicle.service_count, 1)
        action = vehicle.action_view_services()
        self.assertEqual(
            self.env["resource.asset.log"].search(action["domain"]).amount, 150
        )

    def test_mail_to_drivers_reaches_the_driver_partner(self):
        partner = self.env["res.partner"].create(
            {"name": "Carla", "email": "carla@example.com"}
        )
        carla = partner._get_or_create_resources(self.env["res.company"])
        vehicle = self._vehicle()
        vehicle.operator_id = carla
        wizard = self.env["fleet.vehicle.send.mail"].create(
            {
                "vehicle_ids": [(6, 0, vehicle.ids)],
                "subject": "Tyres",
                "body": "Change them",
            }
        )
        wizard.action_send()
        message = vehicle.message_ids.filtered(lambda m: m.subject == "Tyres")
        self.assertEqual(message.partner_ids, partner)
