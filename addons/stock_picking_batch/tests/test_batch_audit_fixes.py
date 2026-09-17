from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBatchAuditFixes(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.picking_type = cls.env.ref("stock.picking_type_out")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Audit product",
                "is_storable": True,
                "weight": 2.0,
                "volume": 3.0,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.stock_location, 1000
        )

    def _picking(self, quantity=5):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": quantity,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        return picking

    def _batch(self, pickings):
        return self.env["stock.picking.batch"].create(
            {
                "picking_type_id": self.picking_type.id,
                "picking_ids": [Command.set(pickings.ids)],
            }
        )

    def test_merging_batches_without_a_scheduled_date_is_refused_not_crashed(self):
        empty = self.env["stock.picking.batch"].create(
            [{"picking_type_id": self.picking_type.id} for _ in range(2)]
        )
        self.assertFalse(any(empty.mapped("date_planned")))
        empty.action_merge()
        self.assertEqual(len(empty.exists()), 1)

    def test_the_shipping_volume_survives_a_weighed_package(self):
        batch = self._batch(self._picking())
        batch.action_confirm()
        batch.move_line_ids.action_put_in_pack()
        package = batch.move_line_ids.result_package_id
        batch.invalidate_recordset()
        volume_unweighed = batch.estimated_shipping_volume
        package.shipping_weight = 99.0
        batch.invalidate_recordset()
        self.assertEqual(
            batch.estimated_shipping_volume,
            volume_unweighed,
            "weighing a package must not erase the volume of what it holds",
        )
        self.assertEqual(batch.estimated_shipping_volume, 5 * self.product.volume)

    def test_the_shipping_capacity_refreshes_when_its_quantities_move(self):
        batch = self._batch(self._picking())
        self.assertEqual(batch.estimated_shipping_weight, 5 * self.product.weight)
        batch.picking_ids.move_ids.move_line_ids.quantity = 1
        self.assertEqual(
            batch.estimated_shipping_weight,
            1 * self.product.weight,
            "the compute declares no dependency on the quantities it reads",
        )

    def test_show_lots_text_refreshes_when_transfers_are_added(self):
        batch = self.env["stock.picking.batch"].create(
            {"picking_type_id": self.picking_type.id}
        )
        self.assertIs(batch.show_lots_text, False)
        picking = self._picking()
        batch.picking_ids = [Command.link(picking.id)]
        self.assertEqual(batch.show_lots_text, picking.show_lots_text)

    def test_two_batches_inverted_together_keep_their_own_lines(self):
        first, second = self._batch(self._picking()), self._batch(self._picking())
        first_lines, second_lines = first.move_line_ids, second.move_line_ids
        first.move_line_ids = first_lines
        second.move_line_ids = second_lines
        self.env.flush_all()
        self.assertTrue(second_lines.exists())
        self.assertEqual(second.move_line_ids, second_lines)
        self.assertEqual(first.move_line_ids, first_lines)

    def test_a_sequence_without_a_slash_still_names_the_batch(self):
        self.env.ref("stock.seq_picking_batch").prefix = "BATCH-"
        name = self.env["stock.picking.batch"]._prepare_name(
            self.picking_type, "picking.batch", self.env.company.id
        )
        self.assertIn(self.picking_type.sequence_code, name)

    def test_an_operation_type_numbers_its_batches_on_its_own_sequence(self):
        shared = self.env.ref("stock.seq_picking_batch")
        type_code = self.picking_type.sequence_code
        self.env["ir.sequence"].create(
            {
                "name": f"Batch Transfer {type_code}",
                "code": f"picking.batch.{type_code.lower()}",
                "prefix": "BATCH/",
                "padding": 4,
                "company_id": False,
            }
        )
        shared_before = shared.number_next_actual
        name = self.env["stock.picking.batch"]._prepare_name(
            self.picking_type, "picking.batch", self.env.company.id
        )
        self.assertEqual(name, f"BATCH/{type_code}/0001")
        self.assertEqual(
            shared.number_next_actual,
            shared_before,
            "a type with its own counter must not consume the shared one",
        )

    def test_a_type_without_its_own_sequence_draws_from_the_shared_counter(self):
        shared = self.env.ref("stock.seq_picking_batch")
        picking_type = self.picking_type.copy({"sequence_code": "NOSEQ"})
        shared_before = shared.number_next_actual
        name = self.env["stock.picking.batch"]._prepare_name(
            picking_type, "picking.batch", self.env.company.id
        )
        self.assertIn("/NOSEQ/", name)
        self.assertEqual(shared.number_next_actual, shared_before + 1)

    def test_negative_batch_limits_are_refused(self):
        picking_type = self.picking_type.copy({"sequence_code": "AUDIT"})
        with self.assertRaises(ValidationError):
            picking_type.batch_max_lines = -1
        with self.assertRaises(ValidationError):
            picking_type.batch_max_pickings = -1

    def test_auto_batch_cannot_be_left_without_any_grouping_key(self):
        picking_type = self.picking_type.copy({"sequence_code": "AUDIT2"})
        picking_type.write(
            {
                "auto_batch": True,
                "batch_group_by_partner": False,
                "batch_group_by_destination": False,
                "batch_group_by_src_loc": False,
                "batch_group_by_dest_loc": False,
                "wave_group_by_category": False,
                "wave_group_by_location": False,
                "wave_group_by_product": True,
            }
        )
        with self.assertRaises(ValidationError):
            picking_type.wave_group_by_product = False

    def test_an_auto_batch_of_two_transfers_keeps_the_responsible(self):
        picking_type = self.picking_type.copy({"sequence_code": "AUDIT3"})
        picking_type.write(
            {
                "auto_batch": True,
                "batch_auto_confirm": True,
                "batch_group_by_partner": True,
                "batch_group_by_destination": False,
                "batch_group_by_src_loc": False,
                "batch_group_by_dest_loc": False,
                "wave_group_by_product": False,
                "wave_group_by_category": False,
                "wave_group_by_location": False,
            }
        )
        picker = self.env["res.users"].create({"name": "Picker", "login": "audit_pick"})
        partner = self.env["res.partner"].create({"name": "Audit partner"})
        pickings = self.env["stock.picking"].create(
            [
                {
                    "picking_type_id": picking_type.id,
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.customer_location.id,
                    "partner_id": partner.id,
                    "user_id": picker.id,
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_uom_qty": 1,
                                "location_id": self.stock_location.id,
                                "location_dest_id": self.customer_location.id,
                            }
                        )
                    ],
                }
                for _ in range(2)
            ]
        )
        pickings.action_confirm()
        pickings.action_assign()
        self.assertEqual(len(pickings.batch_id), 1)
        self.assertEqual(pickings.batch_id.user_id, picker)

    def test_the_grouping_criteria_drive_every_batch_path(self):
        criteria = self.picking_type._get_batch_grouping_criteria()
        self.assertEqual(list(criteria), self.picking_type._get_batch_group_by_keys())
        for criterion in criteria.values():
            self.assertTrue(criterion.picking_path)
            self.assertEqual(
                criterion.batch_path, f"picking_ids.{criterion.picking_path}"
            )

    def test_a_wave_criterion_reads_from_the_move_lines(self):
        for criterion in self.picking_type._get_wave_grouping_criteria().values():
            self.assertFalse(criterion.picking_path)
            self.assertEqual(
                criterion.batch_path, f"move_line_ids.{criterion.line_path}"
            )

    def test_each_batch_takes_its_operation_type_from_its_own_transfers(self):
        other_type = self.picking_type.copy({"sequence_code": "AUDIT4"})
        first = self._picking()
        second = self._picking()
        second.picking_type_id = other_type
        batches = self.env["stock.picking.batch"].create([{"name": "a"}, {"name": "b"}])
        batches[0].picking_ids = [Command.link(first.id)]
        batches[1].picking_ids = [Command.link(second.id)]
        self.assertEqual(batches[0].picking_type_id, self.picking_type)
        self.assertEqual(batches[1].picking_type_id, other_type)

    def test_waving_a_zero_line_of_a_partly_picked_move_is_a_no_op(self):
        loc_a, loc_b = self.env["stock.location"].create(
            [
                {"name": "Audit A", "location_id": self.stock_location.id},
                {"name": "Audit B", "location_id": self.stock_location.id},
            ]
        )
        product = self.env["product.product"].create(
            {"name": "Two lines", "is_storable": True}
        )
        for location in (loc_a, loc_b):
            self.env["stock.quant"]._update_available_quantity(product, location, 5)
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": 10,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        move = picking.move_ids
        self.assertEqual(len(move.move_line_ids), 2, "the fixture is two lines")
        zero_line = move.move_line_ids[0]
        zero_line.quantity = 0

        wave = self.env["stock.picking.batch"].create(
            {"is_wave": True, "picking_type_id": self.picking_type.id}
        )
        vals = zero_line._prepare_wave_picking_vals(wave, picking, zero_line)
        self.assertIsNone(vals, "a move that splits to nothing moves no line")
        self.assertEqual(move.picking_id, picking, "and the move stays put")
        self.assertEqual(len(move.move_line_ids), 2)

    def test_an_empty_batch_cannot_be_confirmed(self):
        batch = self.env["stock.picking.batch"].create(
            {"picking_type_id": self.picking_type.id}
        )
        with self.assertRaises(UserError):
            batch.action_confirm()

    def test_an_in_progress_batch_emptied_from_the_picking_side_is_cancelled(self):
        picking = self._picking()
        batch = self._batch(picking)
        batch.action_confirm()
        picking.batch_id = False
        self.assertEqual(batch.state, "cancel")

    def test_a_draft_batch_emptied_from_the_picking_side_stays_draft(self):
        picking = self._picking()
        batch = self._batch(picking)
        other = self.env["stock.picking.batch"].create(
            {"picking_type_id": self.picking_type.id}
        )
        picking.batch_id = other
        self.assertEqual(batch.state, "draft")
        self.assertEqual(other.picking_ids, picking)

    def test_waving_every_line_of_a_transfer_links_it_whole_despite_a_zeroed_line(
        self,
    ):
        other_product = self.env["product.product"].create(
            {"name": "Audit other", "is_storable": True}
        )
        self.env["stock.quant"]._update_available_quantity(
            other_product, self.stock_location, 10
        )
        picking = self._picking()
        picking.move_ids.move_line_ids.quantity = 0
        picking.write(
            {
                "move_ids": [
                    Command.create(
                        {
                            "product_id": other_product.id,
                            "product_uom_qty": 2,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    )
                ]
            }
        )
        picking.action_assign()
        moves = picking.move_ids
        self.assertEqual(len(moves.move_line_ids), 2)
        pickings_before = self.env["stock.picking"].search_count([])
        wave = self.env["stock.picking.batch"].create(
            {"is_wave": True, "picking_type_id": self.picking_type.id}
        )
        picking.move_line_ids._add_to_wave(wave)
        self.assertEqual(wave.picking_ids, picking, "the whole transfer joins")
        self.assertEqual(picking.move_ids, moves, "and keeps every move")
        self.assertEqual(
            self.env["stock.picking"].search_count([]),
            pickings_before,
            "no copy of the transfer is split off",
        )

    def test_the_wave_wizard_in_new_mode_ignores_a_stale_existing_wave(self):
        picking = self._picking()
        stale = self.env["stock.picking.batch"].create(
            {"is_wave": True, "picking_type_id": self.picking_type.id}
        )
        wizard = (
            self.env["stock.add.to.wave"]
            .with_context(
                active_model="stock.move.line", active_ids=picking.move_line_ids.ids
            )
            .create({"mode": "new", "wave_id": stale.id})
        )
        wizard.attach_pickings()
        self.assertTrue(picking.batch_id.is_wave)
        self.assertNotEqual(picking.batch_id, stale)

    def test_merging_moves_the_transfers_and_nothing_else(self):
        first, second = self._batch(self._picking()), self._batch(self._picking())
        lines = (first | second).move_line_ids
        (first | second).action_merge()
        self.assertFalse(second.exists())
        self.assertEqual(first.move_line_ids, lines)
        self.assertEqual(len(first.picking_ids), 2)

    def test_a_cancelled_transfer_leaves_its_batch_and_a_wrong_type_is_refused(self):
        cancelled, kept = self._picking(), self._picking()
        batch = self._batch(cancelled | kept)
        batch.action_confirm()
        cancelled.action_cancel()
        self.assertEqual(batch.picking_ids, kept)
        self.assertEqual(batch.state, "in_progress")
        other_type = self.picking_type.copy({"sequence_code": "AUDIT5"})
        with self.assertRaises(UserError):
            batch.picking_type_id = other_type

    def test_reconfirming_reserved_transfers_batches_them_once_auto_batch_is_on(self):
        picking_type = self.picking_type.copy({"sequence_code": "AUDIT6"})
        partner = self.env["res.partner"].create({"name": "Late partner"})
        pickings = self.env["stock.picking"].create(
            [
                {
                    "picking_type_id": picking_type.id,
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.customer_location.id,
                    "partner_id": partner.id,
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_uom_qty": 1,
                                "location_id": self.stock_location.id,
                                "location_dest_id": self.customer_location.id,
                            }
                        )
                    ],
                }
                for _ in range(2)
            ]
        )
        pickings.action_confirm()
        pickings.action_assign()
        self.assertEqual(pickings.mapped("state"), ["assigned", "assigned"])
        self.assertFalse(pickings.batch_id)
        picking_type.write({"auto_batch": True, "batch_group_by_partner": True})
        pickings.action_confirm()
        self.assertEqual(len(pickings.batch_id), 1)

    def test_validating_a_batch_with_nothing_processed_is_refused(self):
        pickings = self._picking() | self._picking()
        batch = self._batch(pickings)
        batch.action_confirm()
        pickings.move_ids.quantity = 0
        with self.assertRaises(UserError):
            batch.action_done()
        self.assertEqual(batch.state, "in_progress")
        self.assertEqual(batch.picking_ids, pickings)

    def test_a_batch_created_with_its_default_name_is_numbered(self):
        batch = self.env["stock.picking.batch"].create(
            {"name": "New", "picking_type_id": self.picking_type.id}
        )
        self.assertNotEqual(batch.name, "New")
        self.assertIn(self.picking_type.sequence_code, batch.name)
        kept = self.env["stock.picking.batch"].create(
            {"name": "Given", "picking_type_id": self.picking_type.id}
        )
        self.assertEqual(kept.name, "Given")

    def test_writing_the_scheduled_date_reaches_every_transfer(self):
        pickings = self._picking() | self._picking()
        batch = self._batch(pickings)
        date = fields.Datetime.to_datetime("2030-01-02 03:04:05")
        batch.write({"date_planned": date})
        self.assertEqual(set(pickings.mapped("date_planned")), {date})
        self.assertEqual(batch.date_planned, date)

    def test_merging_takes_the_earliest_date_from_the_transfers_themselves(self):
        first, second = self._batch(self._picking()), self._batch(self._picking())
        early = fields.Datetime.to_datetime("2020-01-01 00:00:00")
        second.date_planned = early
        (first | second).action_merge()
        self.assertEqual(first.date_planned, early)

    def _auto_wave_type(self, **flags):
        picking_type = self.picking_type.copy({"sequence_code": "AUDITW"})
        picking_type.write(
            {
                "auto_batch": True,
                "batch_group_by_partner": False,
                "batch_group_by_destination": False,
                "batch_group_by_src_loc": False,
                "batch_group_by_dest_loc": False,
                "wave_group_by_product": False,
                "wave_group_by_category": False,
                "wave_group_by_location": False,
                **flags,
            }
        )
        return picking_type

    def _typed_picking(self, picking_type, product=None, location=None):
        product = product or self.product
        location = location or self.stock_location
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": location.id,
                "location_dest_id": self.customer_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "location_id": location.id,
                            "location_dest_id": self.customer_location.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        return picking

    def test_an_empty_wave_declaring_its_product_is_filled_by_auto_waving(self):
        picking_type = self._auto_wave_type(wave_group_by_product=True)
        other = self.env["product.product"].create(
            {"name": "Audit other", "is_storable": True}
        )
        self.env["stock.quant"]._update_available_quantity(
            other, self.stock_location, 10
        )
        declared = self.env["stock.picking.batch"].create(
            {
                "is_wave": True,
                "picking_type_id": picking_type.id,
                "wave_product_id": self.product.id,
            }
        )
        stranger = self._typed_picking(picking_type, product=other)
        self.assertNotEqual(stranger.batch_id, declared)
        mine = self._typed_picking(picking_type)
        self.assertEqual(mine.batch_id, declared)
        self.assertEqual(declared.wave_product_id, self.product)

    def test_an_empty_wave_with_no_declaration_is_still_never_filled(self):
        picking_type = self._auto_wave_type(wave_group_by_product=True)
        blank = self.env["stock.picking.batch"].create(
            {"is_wave": True, "picking_type_id": picking_type.id}
        )
        picking = self._typed_picking(picking_type)
        self.assertTrue(picking.batch_id.is_wave)
        self.assertNotEqual(picking.batch_id, blank)

    def test_the_declared_values_follow_the_lines_once_the_wave_holds_some(self):
        picking_type = self._auto_wave_type(wave_group_by_product=True)
        picking = self._typed_picking(picking_type)
        wave = picking.batch_id
        self.assertEqual(wave.wave_product_id, self.product)
        self.assertEqual(wave.wave_partner_id, picking.partner_id)
        self.assertEqual(wave.wave_source_location_id, self.stock_location)

    def test_an_empty_wave_declaring_its_location_is_filled_by_location_waving(
        self,
    ):
        shelf = self.env["stock.location"].create(
            {"name": "Audit shelf", "location_id": self.stock_location.id}
        )
        self.env["stock.quant"]._update_available_quantity(self.product, shelf, 10)
        picking_type = self._auto_wave_type(
            wave_group_by_location=True,
            wave_location_ids=[Command.set(shelf.ids)],
        )
        declared = self.env["stock.picking.batch"].create(
            {
                "is_wave": True,
                "picking_type_id": picking_type.id,
                "wave_location_id": shelf.id,
            }
        )
        picking = self._typed_picking(picking_type, location=shelf)
        self.assertEqual(picking.batch_id, declared)
        self.assertEqual(declared.wave_location_id, shelf)

    def test_joining_a_batch_without_a_responsible_keeps_the_transfers_own(self):
        picker = self.env["res.users"].create({"name": "Keeper", "login": "audit_keep"})
        pickings = self._picking() | self._picking()
        pickings.user_id = picker
        messages_before = len(pickings.message_ids)
        batch = self.env["stock.picking.batch"].create(
            {"picking_type_id": self.picking_type.id}
        )
        pickings.batch_id = batch
        self.assertEqual(pickings.user_id, picker)
        self.assertEqual(len(pickings.message_ids), messages_before)
        batch.user_id = self.env.user
        self.assertEqual(pickings.user_id, self.env.user)

    def test_joining_a_batch_with_a_responsible_takes_it(self):
        picking = self._picking()
        batch = self.env["stock.picking.batch"].create(
            {"picking_type_id": self.picking_type.id, "user_id": self.env.uid}
        )
        picking.batch_id = batch
        self.assertEqual(picking.user_id, self.env.user)
