from psycopg.errors import NotNullViolation

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBoxesAreDevices(TransactionCase):
    """A box and the things it carries are rows of the one device registry,
    so custody, maintenance and an asset see them as they see any device."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.box = cls.env["iot.box"].create(
            {
                "name": "Counter",
                "identifier": "counter-box",
                "ip": "10.1.2.3",
                "version": "L25.07",
            }
        )

    def test_a_box_is_a_device(self):
        self.assertTrue(self.box.device_id)
        self.assertEqual(self.box.device_id.name, "Counter")
        self.assertEqual(self.box.device_id.identifier, "counter-box")
        self.assertEqual(self.box.device_id.endpoint, "10.1.2.3")
        self.assertEqual(
            self.box.device_category_id,
            self.env.ref("iot.kind_iot_box"),
        )

    def test_a_box_pushes(self):
        # Nothing dials a box: it calls /iot/log and /iot/get_handlers itself.
        self.assertEqual(self.box.device_id.link_mode, "push")

    def test_a_peripheral_is_a_part_of_its_box(self):
        scale = self.env["iot.device"].create(
            {
                "name": "Counter scale",
                "identifier": "counter-scale",
                "iot_id": self.box.id,
                "type": "scale",
            }
        )

        self.assertEqual(scale.device_id.parent_id, self.box.device_id)
        self.assertIn(scale.device_id, self.box.device_id.child_ids)
        self.assertEqual(scale.device_category_id, self.env.ref("iot.kind_iot_scale"))

    def test_a_peripheral_takes_the_company_of_its_box(self):
        company = self.env["res.company"].create({"name": "Second"})
        self.box.company_id = company
        printer = self.env["iot.device"].create(
            {
                "name": "Ticket",
                "identifier": "counter-ticket",
                "iot_id": self.box.id,
                "type": "printer",
            }
        )

        self.assertEqual(printer.device_id.company_id, company)

    def test_a_peripheral_that_changes_type_changes_kind(self):
        device = self.env["iot.device"].create(
            {
                "name": "Unknown",
                "identifier": "counter-unknown",
                "iot_id": self.box.id,
                "type": "device",
            }
        )

        device.type = "display"

        self.assertEqual(
            device.device_category_id, self.env.ref("iot.kind_iot_display")
        )

    def test_every_type_the_box_can_report_names_a_kind(self):
        # A type with no kind would land its devices in the registry with no
        # place in it, which is the failure this fold exists to prevent.
        missing = [
            value
            for value, _label in self.env["iot.device"]._fields["type"].selection
            if not self.env.ref(f"iot.kind_iot_{value}", raise_if_not_found=False)
        ]

        self.assertFalse(missing, f"no device.kind for {missing}")

    def test_a_box_that_goes_takes_its_registry_row_and_its_parts(self):
        scale = self.env["iot.device"].create(
            {
                "name": "Going",
                "identifier": "counter-going",
                "iot_id": self.box.id,
                "type": "scale",
            }
        )
        registry_row = self.box.device_id
        part_row = scale.device_id

        self.box.unlink()

        self.assertFalse(registry_row.exists())
        self.assertFalse(part_row.exists())
        self.assertFalse(scale.exists())

    def test_the_registry_finds_a_peripheral_by_what_the_box_calls_it(self):
        self.env["iot.device"].create(
            {
                "name": "Findable",
                "identifier": "findable-1",
                "iot_id": self.box.id,
                "type": "printer",
            }
        )

        found = self.env["device.device"].search([("identifier", "=", "findable-1")])

        self.assertEqual(len(found), 1)
        self.assertEqual(found.parent_id, self.box.device_id)

    def test_the_registry_refuses_a_peripheral_it_cannot_name(self):
        # Identity is what a registry is for: the box reports an identifier
        # with every device it finds, and one that carries none is not a row.
        with self.assertRaises(NotNullViolation):
            with self.env.cr.savepoint():
                self.env["iot.device"].create(
                    {"name": "Nameless", "iot_id": self.box.id, "type": "scale"}
                )
