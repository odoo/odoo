from lxml import etree

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBatchMoveDetails(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.picking_type = cls.env.ref("stock.picking_type_out")
        cls.product = cls.env["product.product"].create(
            {"name": "Waved product", "is_storable": True}
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.stock_location, 100
        )
        cls.deco, cls.gemini = cls.env["res.partner"].create(
            [{"name": "Deco Addict"}, {"name": "Gemini Furniture"}]
        )
        cls.wave = cls.env["stock.picking.batch"].create(
            {"is_wave": True, "picking_type_id": cls.picking_type.id}
        )
        cls.picking_deco = cls._picking(cls.deco)
        cls.picking_gemini = cls._picking(cls.gemini)
        (cls.picking_deco | cls.picking_gemini).batch_id = cls.wave

    @classmethod
    def _picking(cls, partner):
        return cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.picking_type.id,
                "partner_id": partner.id,
                "location_id": cls.stock_location.id,
                "location_dest_id": cls.customer_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 3,
                            "location_id": cls.stock_location.id,
                            "location_dest_id": cls.customer_location.id,
                        }
                    )
                ],
            }
        )

    def test_the_details_wizard_of_a_waved_move_asks_for_the_transfer(self):
        move = self.picking_deco.move_ids
        context = move.with_context(show_picking=True).action_show_details()["context"]
        self.assertEqual(context["default_picking_id"], self.picking_deco.id)
        self.assertTrue(
            context.get("display_name_partner"),
            "opened from a wave, the wizard must name the transfer with its "
            "contact: a wave mixes transfers of several partners",
        )

    def test_a_transfer_named_for_the_wizard_carries_its_contact(self):
        picking = self.picking_gemini
        self.assertEqual(
            picking.with_context(display_name_partner=True).display_name,
            f"{picking.name} - {self.gemini.display_name}",
        )

    def test_a_transfer_without_that_context_is_named_as_before(self):
        picking = self.picking_gemini
        self.assertEqual(picking.display_name, picking.name)

    def test_a_transfer_with_no_contact_is_named_as_before(self):
        picking = self._picking(self.env["res.partner"])
        self.assertFalse(picking.partner_id)
        self.assertEqual(
            picking.with_context(display_name_partner=True).display_name, picking.name
        )

    def test_the_details_wizard_offers_the_transfer_field(self):
        view = self.env.ref("stock.view_stock_move_form_operations")
        arch = etree.fromstring(
            self.env["stock.move"].get_view(view.id, "form")["arch"]
        )
        nodes = arch.xpath('//group[@name="product_qty"]//field[@name="picking_id"]')
        self.assertTrue(
            nodes, "the wizard shows no transfer inside its quantities group"
        )
        self.assertEqual(nodes[0].get("invisible"), "not context.get('show_picking')")

    def test_the_transfer_default_survives_without_the_new_context_key(self):
        move = self.picking_deco.move_ids
        context = move.action_show_details()["context"]
        self.assertEqual(
            context["default_picking_id"],
            self.picking_deco.id,
            "the pre-existing default must not be narrowed by the new guard",
        )
        self.assertFalse(context.get("display_name_partner"))

    def test_the_batch_move_list_asks_for_the_transfer_and_names_its_button(self):
        view = self.env.ref(
            "stock_picking_batch.view_stock_move_list_picking_inherited"
        )
        arch = etree.fromstring(
            self.env["stock.move"].get_view(view.id, "list")["arch"]
        )
        buttons = arch.xpath('//button[@name="action_show_details"]')
        self.assertTrue(buttons, "the batch move list lost its Details button")
        self.assertEqual(buttons[0].get("context"), "{'show_picking': True}")
        self.assertEqual(
            buttons[0].get("string"),
            "Details",
            "the same button on the transfer form's move list is labelled, and "
            "that is the list this one replaces in batch mode",
        )
