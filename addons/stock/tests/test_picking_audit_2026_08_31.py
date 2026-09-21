from odoo import Command
from odoo.tests import TransactionCase


class PickingAuditCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.type_in = cls.env["stock.picking.type"].search(
            [("code", "=", "incoming"), ("warehouse_id", "=", cls.warehouse.id)],
            limit=1,
        )
        cls.type_out = cls.env["stock.picking.type"].search(
            [("code", "=", "outgoing"), ("warehouse_id", "=", cls.warehouse.id)],
            limit=1,
        )
        assert cls.type_in.sequence_id and cls.type_out.sequence_id
        cls.product = cls.env["product.product"].create(
            {"name": "Picking audit product", "is_storable": True},
        )

    def _picking(self, picking_type=None, quantity=3.0):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": (picking_type or self.type_in).id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": quantity,
                        },
                    ),
                ],
            },
        )


class TestCancellationIsNotALatch(PickingAuditCase):
    def test_a_cancelled_transfer_that_regains_a_line_is_draft_again(self):
        picking = self._picking()
        picking.action_confirm()
        picking.action_cancel()
        self.assertEqual(picking.state, "cancel")
        self.assertTrue(picking.is_cancelled)

        picking.move_ids.unlink()
        self.assertEqual(picking.state, "cancel")

        picking.write(
            {
                "move_ids": [
                    Command.create(
                        {"product_id": self.product.id, "product_uom_qty": 1.0},
                    ),
                ],
            },
        )
        picking.invalidate_recordset()
        self.assertEqual(picking.state, "draft")
        self.assertFalse(picking.is_cancelled)

    def test_emptying_an_uncancelled_transfer_leaves_it_draft(self):
        picking = self._picking()
        picking.action_confirm()
        picking.action_cancel()
        picking.move_ids.unlink()
        picking.write(
            {
                "move_ids": [
                    Command.create(
                        {"product_id": self.product.id, "product_uom_qty": 1.0},
                    ),
                ],
            },
        )
        picking.move_ids.unlink()
        picking.invalidate_recordset()
        self.assertEqual(picking.state, "draft")

    def test_confirming_a_cancelled_transfer_releases_the_flag(self):
        picking = self._picking()
        picking.action_confirm()
        picking.action_cancel()
        picking.write(
            {
                "move_ids": [
                    Command.create(
                        {"product_id": self.product.id, "product_uom_qty": 1.0},
                    ),
                ],
            },
        )
        picking.action_confirm()
        self.assertFalse(picking.is_cancelled)
        self.assertNotEqual(picking.state, "cancel")

    def test_a_transfer_cancelled_while_empty_still_reads_cancelled(self):
        picking = self.env["stock.picking"].create(
            {"picking_type_id": self.type_in.id},
        )
        picking.action_cancel()
        picking.invalidate_recordset()
        self.assertTrue(picking.is_cancelled)
        self.assertEqual(picking.state, "cancel")


class TestLocationPropagationIsGated(PickingAuditCase):
    def test_the_trigger_set_is_derived_from_the_registry(self):
        picking = self.env["stock.picking"]
        field_depends = self.env.registry.field_depends
        expected = {"location_id", "location_dest_id"}
        for name in ("location_id", "location_dest_id"):
            expected.update(
                dependency.split(".")[0]
                for dependency in field_depends[picking._fields[name]]
            )
        self.assertEqual(
            picking._get_location_trigger_fields(),
            frozenset(expected),
            "the gate must follow the registry, so an addon that adds a depends"
            " to either location compute cannot leave it stale",
        )

    def test_the_trigger_set_holds_the_fields_that_move_a_location(self):
        self.assertLessEqual(
            {"location_id", "location_dest_id", "picking_type_id", "partner_id"},
            self.env["stock.picking"]._get_location_trigger_fields(),
        )

    def test_a_write_that_cannot_move_a_location_takes_no_snapshot(self):
        pickings = self.env["stock.picking"].concat(
            *(self._picking() for _ in range(3)),
        )
        pickings.action_confirm()
        snapshots = []
        model = type(self.env["stock.picking"])
        original = model._propagate_locations_to_moves

        def counting_propagate(records, locations_before):
            snapshots.append(len(locations_before))
            return original(records, locations_before)

        model._propagate_locations_to_moves = counting_propagate
        try:
            pickings.write({"is_locked": False})
            irrelevant = list(snapshots)
            snapshots.clear()
            pickings.write({"location_id": self.warehouse.lot_stock_id.id})
        finally:
            model._propagate_locations_to_moves = original

        self.assertEqual(irrelevant, [0], "is_locked cannot move a location")
        self.assertEqual(snapshots, [3], "location_id still propagates to moves")

    def test_renaming_on_a_type_change_adds_no_snapshot_work(self):
        pickings = self.env["stock.picking"].concat(
            *(self._picking() for _ in range(5)),
        )
        snapshots = []
        model = type(self.env["stock.picking"])
        original = model._propagate_locations_to_moves

        def counting_propagate(records, locations_before):
            snapshots.append(len(locations_before))
            return original(records, locations_before)

        model._propagate_locations_to_moves = counting_propagate
        try:
            pickings.write({"picking_type_id": self.type_out.id})
        finally:
            model._propagate_locations_to_moves = original

        self.assertEqual(
            pickings.picking_type_id,
            self.type_out,
            "the write must really change the type, or this test proves nothing",
        )
        self.assertEqual(
            sum(snapshots),
            5,
            "the batch is snapshotted once; the five nested name writes add none",
        )
        self.assertEqual(len(set(pickings.mapped("name"))), 5)

    def test_a_source_location_write_still_reaches_the_moves(self):
        picking = self._picking(picking_type=self.type_out)
        picking.action_confirm()
        shelf = self.env["stock.location"].create(
            {
                "name": "Audit shelf",
                "usage": "internal",
                "location_id": self.warehouse.lot_stock_id.id,
            },
        )
        self.assertNotEqual(picking.move_ids.location_id, shelf)
        picking.write({"location_id": shelf.id})
        self.assertEqual(picking.move_ids.location_id, shelf)

    def test_a_partner_write_that_moves_the_location_reaches_the_moves(self):
        own_supplier = self.env["stock.location"].create(
            {
                "name": "Audit vendor location",
                "usage": "supplier",
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
            },
        )
        partner = self.env["res.partner"].create({"name": "Audit vendor"})
        partner.property_stock_supplier = own_supplier
        picking = self._picking()
        picking.action_confirm()
        self.assertNotEqual(picking.location_id, own_supplier)

        picking.write({"partner_id": partner.id})

        self.assertEqual(
            picking.location_id,
            own_supplier,
            "writing partner_id must still recompute the source location",
        )
        self.assertEqual(picking.move_ids.location_id, own_supplier)


class TestAllocationHelpersHaveOneHome(PickingAuditCase):
    def test_the_picking_model_does_not_shadow_the_move_domain(self):
        picking = self.env["stock.picking"]
        for shadowed in (
            "_get_domain_allocatable_demand",
            "_get_allocation_allowed_move_states",
            "_get_allocation_source_location_ids",
        ):
            self.assertFalse(
                hasattr(picking, shadowed),
                f"stock.picking.{shadowed} duplicates a live helper on another"
                " model; an addon overriding it would be overriding nothing",
            )

    def test_the_live_helpers_are_where_the_call_sites_look(self):
        self.assertTrue(
            hasattr(self.env["stock.move"], "_get_domain_allocatable_demand"),
        )
        self.assertTrue(
            hasattr(self.env["stock.move"], "_get_allocation_allowed_states"),
        )
        self.assertTrue(
            hasattr(self.env["stock.location"], "_get_allocation_source_ids"),
        )

    def test_the_move_domain_narrows_when_assigned_is_excluded(self):
        Move = self.env["stock.move"]

        def states(domain):
            return next(leaf[2] for leaf in domain if leaf[0] == "state")

        self.assertIn(
            "assigned",
            states(Move._get_domain_allocatable_demand([1], [2])),
        )
        self.assertNotIn(
            "assigned",
            states(
                Move._get_domain_allocatable_demand(
                    [1],
                    [2],
                    include_assigned=False,
                ),
            ),
        )


class TestAggregatesDoNotReadTheLines(PickingAuditCase):
    def test_shipping_volume_aggregates_without_loading_the_moves(self):
        pickings = self.env["stock.picking"].concat(
            *(self._picking() for _ in range(5)),
        )
        self.env.flush_all()
        self.env.invalidate_all()

        move_ids_field = self.env["stock.picking"]._fields["move_ids"]
        self.assertFalse(
            self.env.cache.get_records(pickings, move_ids_field),
            "the fixture must start with no line ids cached",
        )

        pickings.mapped("shipping_volume")

        self.assertFalse(
            self.env.cache.get_records(pickings, move_ids_field),
            "_read_group aggregates in SQL, so reaching the comodel must not"
            " pull every line id of every transfer",
        )

    def test_shipping_volume_is_still_right(self):
        picking = self._picking(quantity=4.0)
        picking.move_ids.product_id.volume = 2.5
        picking.action_confirm()
        picking.move_ids.quantity = 4.0
        self.env.flush_all()
        self.assertAlmostEqual(
            picking.shipping_volume,
            10.0,
            msg="shipping_volume sums the done quantity, not the demand",
        )


class TestAvailabilitySearchMatchesTheField(PickingAuditCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stocked = cls.env["product.product"].create(
            {"name": "Audit stocked", "is_storable": True},
        )
        cls.starved = cls.env["product.product"].create(
            {"name": "Audit starved", "is_storable": True},
        )
        cls.service = cls.env["product.product"].create(
            {"name": "Audit consumable", "type": "consu", "is_storable": False},
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.stocked,
            cls.warehouse.lot_stock_id,
            500,
        )

    def _outgoing(self, products, quantity=1.0):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.type_out.id,
                "move_ids": [
                    Command.create(
                        {"product_id": p.id, "product_uom_qty": quantity},
                    )
                    for p in products
                ],
            },
        )

    def test_the_search_agrees_with_the_field_on_every_state(self):
        pickings = self.env["stock.picking"].concat(
            self._outgoing(self.stocked),
            self._outgoing(self.starved, quantity=900.0),
            self._outgoing(self.service),
            self._outgoing(self.stocked + self.starved, quantity=900.0),
        )
        pickings.action_confirm()
        self.env.flush_all()
        self.env.invalidate_all()

        for state in ("available", "expected", "late"):
            with self.subTest(state=state):
                by_field = pickings.filtered(
                    lambda p, s=state: p.products_availability_state == s,
                )
                by_search = self.env["stock.picking"].search(
                    [
                        ("id", "in", pickings.ids),
                        ("products_availability_state", "in", [state]),
                    ],
                )
                self.assertEqual(
                    by_search,
                    by_field,
                    f"the search and the field disagree on {state!r}",
                )

    def test_a_transfer_of_only_consumables_is_available(self):
        picking = self._outgoing(self.service)
        picking.action_confirm()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(picking.products_availability_state, "available")
        self.assertIn(
            picking,
            self.env["stock.picking"].search(
                [
                    ("id", "=", picking.id),
                    ("products_availability_state", "in", ["available"]),
                ],
            ),
            "a transfer with no move that can decide availability is available,"
            " and the search must still return it",
        )

    def test_a_cancelled_line_does_not_decide_availability(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.type_out.id,
                "move_ids": [
                    Command.create(
                        {"product_id": self.stocked.id, "product_uom_qty": 1.0},
                    ),
                    Command.create(
                        {"product_id": self.starved.id, "product_uom_qty": 900.0},
                    ),
                ],
            },
        )
        picking.action_confirm()
        self.assertEqual(
            picking.products_availability_state,
            "late",
            "the starved line must make it late while it is alive,"
            " or cancelling it proves nothing",
        )
        picking.move_ids.filtered(
            lambda m: m.product_id == self.starved,
        )._action_cancel()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            picking.products_availability_state,
            self.env["stock.picking"]
            .search([("id", "=", picking.id)])
            .products_availability_state,
        )
        self.assertNotIn(
            picking,
            self.env["stock.picking"].search(
                [
                    ("id", "=", picking.id),
                    ("products_availability_state", "in", ["late"]),
                ],
            ),
            "the cancelled shortage must not make the transfer late",
        )

    def test_the_deciding_domain_excludes_what_cannot_decide(self):
        picking = self.env["stock.picking"]
        domain = {
            leaf[0]: leaf[2]
            for leaf in picking._get_domain_availability_deciding_moves()
        }
        self.assertEqual(set(domain["state"]), {"done", "cancel"})
        self.assertTrue(domain["product_id.is_storable"])


class TestPutInPackStaysOnItsOwnTransfer(PickingAuditCase):
    def _ready(self):
        picking = self._picking(quantity=4.0)
        picking.action_confirm()
        picking.move_ids.quantity = 4.0
        self.env.flush_all()
        return picking

    def test_a_context_cannot_redirect_the_pack_to_another_transfer(self):
        mine, theirs = self._ready(), self._ready()
        self.assertFalse(theirs.move_line_ids.result_package_id)

        mine.with_context(
            all_move_line_ids=theirs.move_line_ids.ids,
        ).action_put_in_pack()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertFalse(
            theirs.move_line_ids.result_package_id,
            "action_put_in_pack declares check_singleton and guards on self.state,"
            " so a context key must not make it pack another transfer's lines",
        )
        self.assertTrue(
            mine.move_line_ids.result_package_id,
            "it must still pack the transfer it was actually called on",
        )

    def test_the_widening_within_one_transfer_is_untouched(self):
        picking = self._ready()
        picking.with_context(
            all_move_line_ids=picking.move_line_ids.ids,
        ).action_put_in_pack()
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertTrue(picking.move_line_ids.result_package_id)

    def test_a_done_transfer_is_still_refused(self):
        picking = self._ready()
        picking.move_ids.picked = True
        picking.with_context(skip_backorder=True).button_validate()
        self.env.flush_all()
        self.assertEqual(picking.state, "done")
        self.assertIsNone(picking.action_put_in_pack())


class TestValidationStaysOnTheTransferItWasCalledOn(PickingAuditCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.type_in.create_backorder = "ask"

    def _partial(self):
        picking = self._picking(quantity=10.0)
        picking.action_confirm()
        picking.move_ids.quantity = 4.0
        picking.move_ids.picked = True
        self.env.flush_all()
        return picking

    def test_a_context_cannot_redirect_the_validation_to_another_transfer(self):
        mine, bystander = self._partial(), self._partial()

        action = mine.with_context(
            button_validate_picking_ids=bystander.ids,
        ).button_validate()

        self.assertEqual(action["res_model"], "stock.backorder.confirmation")
        self.assertEqual(
            action["context"]["button_validate_picking_ids"],
            mine.ids,
            "the wizard must be handed the transfer the user opened,"
            " not whatever the incoming context named",
        )
        wizard = (
            self.env["stock.backorder.confirmation"]
            .with_context(**action["context"])
            .create({})
        )
        wizard.process()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            bystander.state,
            "assigned",
            "confirming a backorder dialog must not validate a transfer the user"
            " never opened -- validating moves stock and cannot be undone",
        )
        self.assertEqual(mine.state, "done")

    def test_the_wizard_re_entry_is_unaffected(self):
        picking = self._partial()
        action = picking.button_validate()
        wizard = (
            self.env["stock.backorder.confirmation"]
            .with_context(**action["context"])
            .create({})
        )
        wizard.process()
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(picking.state, "done")
        self.assertTrue(picking.backorder_ids, "the backorder is still created")

    def test_two_transfers_validated_together_keep_both(self):
        pair = self.env["stock.picking"].concat(self._partial(), self._partial())
        action = pair.button_validate()
        self.assertEqual(
            set(action["context"]["button_validate_picking_ids"]),
            set(pair.ids),
        )


class TestAMissingMailTemplateDoesNotBlockDelivery(PickingAuditCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["stock.quant"]._update_available_quantity(
            cls.product,
            cls.warehouse.lot_stock_id,
            100,
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "Audit customer", "email": "audit@example.invalid"},
        )
        cls.env.company.stock_config_id.stock_move_email_validation = True

    def _ready_delivery(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.type_out.id,
                "partner_id": self.customer.id,
                "move_ids": [
                    Command.create(
                        {"product_id": self.product.id, "product_uom_qty": 2.0},
                    ),
                ],
            },
        )
        picking.action_confirm()
        picking.move_ids.quantity = 2.0
        picking.move_ids.picked = True
        self.env.flush_all()
        return picking

    def test_a_deleted_template_does_not_block_validation(self):
        self.env.company.stock_config_id.stock_mail_confirmation_template_id = False
        picking = self._ready_delivery()

        picking.with_context(skip_backorder=True).button_validate()

        self.assertEqual(
            picking.state,
            "done",
            "an absent confirmation template must not stop the goods moving;"
            " it used to raise a bare ValueError out of message_post_with_source",
        )

    def test_the_confirmation_is_still_sent_when_the_template_is_there(self):
        self.assertTrue(
            self.env.company.stock_config_id.stock_mail_confirmation_template_id
        )
        picking = self._ready_delivery()
        before = len(picking.message_ids)

        picking.with_context(skip_backorder=True).button_validate()

        self.assertEqual(picking.state, "done")
        self.assertGreater(
            len(picking.message_ids),
            before,
            "the confirmation message must still be posted",
        )


class TestSingletonActions(PickingAuditCase):
    def test_action_view_packages_declares_its_singleton_contract(self):
        pickings = self.env["stock.picking"].concat(
            *(self._picking() for _ in range(2)),
        )
        with self.assertRaises(ValueError):
            pickings.action_view_packages()

    def test_action_view_packages_still_answers_for_one(self):
        picking = self._picking()
        action = picking.action_view_packages()
        self.assertEqual(action["res_model"], "stock.package")
        self.assertEqual(action["context"]["location_id"], picking.location_id.id)
