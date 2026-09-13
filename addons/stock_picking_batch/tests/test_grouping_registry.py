from odoo.tests import TransactionCase, tagged

from odoo.addons.stock.models.stock_picking_type import GroupingCriterion


@tagged("post_install", "-at_install")
class TestGroupingRegistry(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.picking_type = cls.env.ref("stock.picking_type_out")

    def test_the_registry_lives_in_stock_and_is_filled_by_whoever_owns_a_criterion(
        self,
    ):
        criteria = self.picking_type._get_grouping_criteria()
        for key, criterion in criteria.items():
            self.assertIsInstance(
                criterion,
                GroupingCriterion,
                f"{key} must be the GroupingCriterion stock declares, so a "
                f"module can register one by depending on stock alone.",
            )

    def test_this_module_registers_the_six_criteria_it_owns(self):
        criteria = self.picking_type._get_grouping_criteria()
        self.assertLessEqual(
            {
                "batch_group_by_partner",
                "batch_group_by_destination",
                "batch_group_by_src_loc",
                "batch_group_by_dest_loc",
                "wave_group_by_product",
                "wave_group_by_category",
            },
            set(criteria),
            "A subset rather than an equality on purpose: the registry exists "
            "to be added to, and delivery_stock_picking_batch adds a seventh.",
        )

    def test_a_criterion_counts_as_active_only_while_its_field_is_set(self):
        self.picking_type.batch_group_by_partner = True
        self.picking_type.batch_group_by_src_loc = False
        active = self.picking_type._get_active_batch_criteria()
        self.assertIn("batch_group_by_partner", active)
        self.assertNotIn("batch_group_by_src_loc", active)

    def test_a_picking_level_criterion_and_a_line_level_one_read_different_paths(self):
        criteria = self.picking_type._get_grouping_criteria()
        partner = criteria["batch_group_by_partner"]
        product = criteria["wave_group_by_product"]
        self.assertEqual(partner.batch_path, "picking_ids.partner_id")
        self.assertEqual(product.batch_path, "move_line_ids.product_id")

    def test_a_criterion_whose_label_is_empty_adds_nothing_to_the_description(self):
        self.picking_type.write(
            {
                "auto_batch": True,
                "batch_group_by_partner": True,
                "batch_group_by_src_loc": True,
            }
        )
        # A delivery address created from a form with no name is still a
        # partner the batch groups on; its label is False, not a word.
        company_partner = self.env["res.partner"].create({"name": "Grouped Co"})
        partner = self.env["res.partner"].create(
            {"type": "delivery", "parent_id": company_partner.id}
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type.id,
                "partner_id": partner.id,
                "location_id": self.picking_type.default_location_src_id.id,
                "location_dest_id": self.picking_type.default_location_dest_id.id,
            }
        )
        self.assertFalse(partner.name)
        self.assertEqual(
            picking._get_auto_batch_description(),
            self.picking_type.default_location_src_id.display_name,
        )
