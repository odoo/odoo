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
        assignment = vehicle.assignment_ids.filtered(
            lambda a: a.custody_role == "operator"
        )
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

    def test_a_vehicle_waiting_for_its_plate_is_named_by_what_identifies_it(self):
        awaiting = self._vehicle(plate=False, vin_sn="VIN-4242")

        self.assertEqual(awaiting.display_name, "Probe Motors / Probe One / VIN-4242")

    def test_a_model_carries_its_fuel_specifications(self):
        self.model.product_tmpl_id.write(
            {
                "fuel_tank_capacity": 47,
                "fuel_efficiency_theoretical": 17.5,
                "fuel_efficiency_min": 14.2,
                "fuel_efficiency_max": 20.8,
            }
        )

        self.assertEqual(self._vehicle(plate="PRB-FUEL").fuel_tank_capacity, 47)
        self.assertTrue(self.model.product_tmpl_id.fuel_efficiency_uom_name)

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


@tagged("post_install", "-at_install")
class TestVehicleIsItsOwnModel(TransactionCase):
    """A vehicle's rows live in `resource_asset_vehicle`, which inherits
    `resource_asset`. Everything a vehicle is stays declared on the root, so a
    reference held as `resource.asset` still reads and writes it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Asset = cls.env["resource.asset"]
        cls.Vehicle = cls.env["resource.asset.vehicle"]
        cls.vehicle_kind = cls.env.ref("resource_asset.kind_vehicle")
        cls.tool_kind = cls.env.ref("resource_asset.kind_tool")

    def test_the_kind_code_is_the_only_name_the_model_needs(self):
        self.assertEqual(
            self.Asset._get_model_for_kind(self.vehicle_kind),
            "resource.asset.vehicle",
        )
        self.assertEqual(
            self.Asset._get_model_for_kind(self.tool_kind), "resource.asset"
        )
        self.assertIn("resource.asset.vehicle", self.Asset._get_model_names_in_tree())

    def test_a_kind_whose_code_names_no_model_is_a_plain_asset(self):
        drone = self.env["resource.asset.kind"].create(
            {"name": "Drone", "code": "drone"}
        )

        self.assertEqual(self.Asset._get_model_for_kind(drone), "resource.asset")

    def test_the_vehicle_table_inherits_the_asset_table(self):
        self.env.cr.execute(
            """
            SELECT p.relname FROM pg_inherits i
              JOIN pg_class c ON c.oid = i.inhrelid
              JOIN pg_class p ON p.oid = i.inhparent
             WHERE c.relname = 'resource_asset_vehicle'
            """
        )
        self.assertEqual(self.env.cr.fetchall(), [("resource_asset",)])

    def test_a_vehicle_created_as_an_asset_lands_in_the_vehicle_model(self):
        """No caller has to know: the kind names the model and the root sends
        the row there."""
        asset = self.Asset.create(
            {"name": "Dispatched", "kind_id": self.vehicle_kind.id}
        )

        self.assertEqual(asset._get_concrete()._name, "resource.asset.vehicle")
        self.assertIn(asset.id, self.Vehicle.search([]).ids)

    def test_a_kind_naming_no_model_stays_an_asset(self):
        asset = self.Asset.create({"name": "Plain", "kind_id": self.tool_kind.id})

        self.assertEqual(asset._get_concrete()._name, "resource.asset")

    def test_a_vehicle_is_read_and_written_through_the_root(self):
        """The whole design rests on this: no caller holding a `resource.asset`
        needs to know the row moved."""
        vehicle = self.Vehicle.create(
            {"name": "Through the root", "kind_id": self.vehicle_kind.id}
        )

        as_asset = self.Asset.browse(vehicle.id)
        self.assertEqual(as_asset.name, "Through the root")
        as_asset.name = "Renamed from the root"
        self.assertEqual(vehicle.name, "Renamed from the root")
        self.assertIn(
            as_asset, self.Asset.search([("name", "=", "Renamed from the root")])
        )

    def test_a_compute_depending_on_the_root_fires_for_a_vehicle(self):
        """`resource.resource.asset_id` depends on `resource.asset.resource_id`,
        and a vehicle writes its own copy of that field. The trigger graph is
        keyed by the Field object, so without the tree expansion this compute
        would never hear about a vehicle."""
        vehicle = self.Vehicle.create(
            {"name": "Triggers", "kind_id": self.vehicle_kind.id}
        )

        self.assertEqual(vehicle.resource_id.asset_id, self.Asset.browse(vehicle.id))
        self.assertIn(vehicle.id, vehicle.resource_id.asset_ids.ids)

    def test_a_vehicle_takes_part_in_the_asset_hierarchy(self):
        """`parent_id` names `resource.asset`, which is this model's tree root,
        so it is a relation on itself here too."""
        whole = self.Asset.create({"name": "Machine", "kind_id": self.tool_kind.id})
        part = self.Vehicle.create(
            {
                "name": "Mounted vehicle",
                "kind_id": self.vehicle_kind.id,
                "parent_id": whole.id,
            }
        )

        self.assertFalse(part._has_cycle("parent_id"))
        self.assertIn(part.id, self.Asset.search([("id", "child_of", whole.id)]).ids)

    def test_creating_a_tool_in_the_vehicle_model_is_refused(self):
        with self.assertRaises(ValidationError):
            self.Vehicle.create({"name": "Drill", "kind_id": self.tool_kind.id})

    def test_an_asset_cannot_be_retyped_into_another_model(self):
        tool = self.Asset.create({"name": "Drill", "kind_id": self.tool_kind.id})

        with self.assertRaises(ValidationError):
            tool.kind_id = self.vehicle_kind

    def test_one_create_call_may_span_models_and_keep_its_order(self):
        created = self.Asset.create(
            [
                {"name": "A vehicle", "kind_id": self.vehicle_kind.id},
                {"name": "A tool", "kind_id": self.tool_kind.id},
                {"name": "Another vehicle", "kind_id": self.vehicle_kind.id},
            ]
        )

        self.assertEqual(
            created.mapped("name"), ["A vehicle", "A tool", "Another vehicle"]
        )
        self.assertEqual(
            [record._get_concrete()._name for record in created],
            ["resource.asset.vehicle", "resource.asset", "resource.asset.vehicle"],
        )

    def test_deleting_through_the_root_deletes_the_vehicle(self):
        vehicle = self.Vehicle.create(
            {"name": "Doomed", "kind_id": self.vehicle_kind.id}
        )
        vehicle_id = vehicle.id

        self.Asset.browse(vehicle_id).unlink()

        self.assertFalse(self.Vehicle.browse(vehicle_id).exists())
        self.assertFalse(self.Asset.browse(vehicle_id).exists())


@tagged("post_install", "-at_install")
class TestVehicleInheritsWhatBindsAnAsset(TransactionCase):
    """A missing access right denies and is noticed at once; a missing record
    rule permits and is noticed by nobody. So a subtype answers to its root's
    rules, while its access rights stay its own."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Vehicle = cls.env["resource.asset.vehicle"]
        cls.kind = cls.env.ref("resource_asset.kind_vehicle")
        cls.other_company = cls.env["res.company"].create({"name": "Elsewhere"})
        cls.user = new_test_user(
            cls.env, login="vehicle_reader", groups="resource_asset.group_asset_user"
        )

    def test_the_multi_company_rule_of_the_asset_binds_the_vehicle(self):
        mine = self.Vehicle.create(
            {
                "name": "Mine",
                "kind_id": self.kind.id,
                "company_id": self.user.company_id.id,
            }
        )
        theirs = self.Vehicle.create(
            {
                "name": "Theirs",
                "kind_id": self.kind.id,
                "company_id": self.other_company.id,
            }
        )

        visible = self.Vehicle.with_user(self.user).search([])

        self.assertIn(mine, visible)
        self.assertNotIn(theirs, visible)

    def test_the_root_rules_are_the_ones_a_subtype_answers_to(self):
        Rule = self.env["ir.rule"]

        self.assertEqual(
            Rule._get_model_names_bound_by_rules("resource.asset.vehicle"),
            ["resource.asset.vehicle", "resource.asset"],
        )
        self.assertEqual(
            Rule._get_model_names_bound_by_rules("resource.asset"),
            ["resource.asset"],
            "a rule written for one subtype must not narrow its siblings",
        )


@tagged("post_install", "-at_install")
class TestFleetActionContexts(TransactionCase):
    """An action's context is stored as source and evaluated without `ref`, and
    a broken expression is defaulted to {} rather than raised. So a context that
    calls `ref` is not an error anyone sees: it is a menu whose New button
    quietly makes the wrong record."""

    def test_every_fleet_action_context_survives_evaluation(self):
        data = self.env["ir.model.data"].search(
            [("module", "=", "fleet"), ("model", "=", "ir.actions.act_window")]
        )
        actions = self.env["ir.actions.act_window"].browse(data.mapped("res_id"))

        empty = [
            action.id
            for action in actions
            if action.context
            and action.context.strip() not in ("{}", "")
            and not action._eval_action_context(action.context)
        ]

        self.assertEqual(empty, [])

    def test_the_vehicle_actions_default_what_they_promise(self):
        vehicle_kind = self.env.ref("resource_asset.kind_vehicle")

        vehicles = self.env.ref("fleet.fleet_vehicle_action")
        models = self.env.ref("fleet.fleet_vehicle_model_action")

        self.assertEqual(
            vehicles._eval_action_context(vehicles.context)["default_kind_id"],
            vehicle_kind.id,
        )
        model_context = models._eval_action_context(models.context)
        self.assertEqual(model_context["default_asset_kind_id"], vehicle_kind.id)
        self.assertEqual(model_context["default_type"], "consu")
        self.assertFalse(model_context["default_sale_ok"])
