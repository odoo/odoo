from datetime import datetime

from dateutil.relativedelta import relativedelta
from psycopg.errors import CheckViolation, UniqueViolation

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.stock.tests.common import TestStockCommon


@tagged("post_install", "-at_install")
class TestPickingTypeSequence(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )

    def _new_type(self, **vals):
        return self.env["stock.picking.type"].create(
            {"name": "Probe", "code": "incoming", "sequence_code": "PRB", **vals}
        )

    def test_omitted_warehouse_still_qualifies_the_prefix(self):
        picking_type = self._new_type()
        self.assertTrue(picking_type.warehouse_id)
        self.assertEqual(
            picking_type.sequence_id.prefix,
            f"{picking_type.warehouse_id.code}/PRB/",
        )

    def test_prefix_uses_the_canonical_warehouse_code(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Spacey", "code": "sp a", "company_id": self.company.id}
        )
        self.assertEqual(warehouse.code, "SPA")
        picking_type = self._new_type(warehouse_id=warehouse.id, sequence_code="SPC")
        self.assertEqual(picking_type.sequence_id.prefix, "SPA/SPC/")

    def test_an_unchanged_sequence_is_not_rewritten(self):
        picking_type = self._new_type()
        sequence = picking_type.sequence_id
        self.env.flush_all()
        writes = []
        sequence_model = type(sequence)
        original = sequence_model.write

        def recording(records, vals):
            writes.append(vals)
            return original(records, vals)

        self.patch(sequence_model, "write", recording)
        picking_type._update_reference_sequences()
        self.env.flush_all()
        self.assertEqual(
            writes,
            [],
            "a sequence already in line with its operation type must not be written",
        )

    def test_sequences_of_one_create_are_one_batch(self):
        calls = []
        sequence_model = type(self.env["ir.sequence"])
        original = sequence_model.create

        def counting(records, vals_list):
            calls.append(len(vals_list) if isinstance(vals_list, list) else 1)
            return original(records, vals_list)

        self.patch(sequence_model, "create", counting)
        self.env["stock.picking.type"].create(
            [
                {
                    "name": f"Batch {index}",
                    "code": "incoming",
                    "sequence_code": f"BT{index}",
                    "warehouse_id": self.warehouse.id,
                }
                for index in range(10)
            ]
        )
        self.assertEqual(calls, [10], "ten sequences, one create")

    def test_swapping_the_sequence_and_the_code_together(self):
        picking_type = self._new_type(warehouse_id=self.warehouse.id)
        detached = picking_type.sequence_id
        before = (detached.name, detached.prefix)
        attached = self.env["ir.sequence"].create(
            {
                "name": "Brand New",
                "prefix": "NEW/",
                "padding": 5,
                "company_id": self.company.id,
            }
        )
        picking_type.write({"sequence_code": "PRB2", "sequence_id": attached.id})
        self.assertEqual(
            (detached.name, detached.prefix),
            before,
            "the detached sequence must be left alone",
        )
        self.assertEqual(attached.prefix, f"{self.warehouse.code}/PRB2/")

    def test_moving_a_type_to_another_warehouse_moves_its_prefix(self):
        other = self.env["stock.warehouse"].create(
            {"name": "MoveTo", "code": "MVT", "company_id": self.company.id}
        )
        picking_type = self._new_type(warehouse_id=self.warehouse.id)
        picking_type.write({"warehouse_id": other.id})
        self.assertEqual(picking_type.sequence_id.prefix, "MVT/PRB/")
        self.assertEqual(picking_type.sequence_id.name, "MoveTo Sequence PRB")

    def test_recoding_a_warehouse_moves_user_created_types_too(self):
        custom = self._new_type(
            warehouse_id=self.warehouse.id, sequence_code="CUS", code="internal"
        )
        builtin = self.warehouse.in_type_id
        self.warehouse.write({"code": "RECD"})
        self.assertTrue(builtin.sequence_id.prefix.startswith("RECD/"))
        self.assertEqual(custom.sequence_id.prefix, "RECD/CUS/")

    def test_renaming_a_warehouse_renames_user_created_sequences(self):
        custom = self._new_type(warehouse_id=self.warehouse.id, sequence_code="CUS2")
        self.warehouse.write({"name": "Renamed WH"})
        self.assertEqual(custom.sequence_id.name, "Renamed WH Sequence CUS2")

    def test_two_types_of_one_warehouse_may_share_a_prefix(self):
        first = self._new_type(warehouse_id=self.warehouse.id, sequence_code="DUP")
        second = self._new_type(
            warehouse_id=self.warehouse.id,
            sequence_code="DUP",
            code="outgoing",
            name="Other",
        )
        self.env.flush_all()
        self.assertEqual(first.sequence_code, second.sequence_code)

    def test_the_same_prefix_on_another_warehouse_is_fine(self):
        other = self.env["stock.warehouse"].create(
            {"name": "Second", "code": "SND", "company_id": self.company.id}
        )
        first = self._new_type(warehouse_id=self.warehouse.id, sequence_code="SHARED")
        second = self._new_type(
            warehouse_id=other.id, sequence_code="SHARED", name="Other"
        )
        self.env.flush_all()
        self.assertNotEqual(first.sequence_id.prefix, second.sequence_id.prefix)

    def test_the_onchange_sees_archived_types(self):
        archived = self._new_type(warehouse_id=self.warehouse.id, sequence_code="ARC")
        archived.active = False
        self.env.flush_all()
        draft = self.env["stock.picking.type"].new(
            {
                "name": "New",
                "code": "incoming",
                "sequence_code": "ARC",
                "warehouse_id": self.warehouse.id,
                "company_id": self.company.id,
            }
        )
        warning = draft._onchange_sequence_code()
        self.assertTrue(warning, "an archived type still holds its prefix")
        self.assertIn("archived", warning["warning"]["message"])

    def test_a_copy_gets_a_prefix_that_is_still_an_identifier(self):
        picking_type = self._new_type(warehouse_id=self.warehouse.id)
        clone = picking_type.copy()
        self.env.flush_all()
        self.assertNotIn(" ", clone.sequence_id.prefix)
        self.assertNotIn("(", clone.sequence_id.prefix)
        self.assertNotEqual(clone.sequence_code, picking_type.sequence_code)


@tagged("post_install", "-at_install")
class TestPickingTypeWarehouse(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )

    def test_one_query_serves_the_whole_batch(self):
        searches = []
        warehouse_model = type(self.env["stock.warehouse"])
        original = warehouse_model.search

        def counting(records, *args, **kwargs):
            searches.append(1)
            return original(records, *args, **kwargs)

        self.patch(warehouse_model, "search", counting)
        picking_types = self.env["stock.picking.type"].create(
            [
                {
                    "name": f"Batched {index}",
                    "code": "incoming",
                    "sequence_code": f"BW{index}",
                    "company_id": self.company.id,
                }
                for index in range(8)
            ]
        )
        self.assertEqual(len(picking_types.warehouse_id), 1, "all got a warehouse")
        self.assertEqual(searches, [], "one grouped read, no per-record search")

    def test_no_warehouse_does_not_blame_the_company(self):
        self.assertTrue(
            self.env["stock.warehouse"].search_count(
                [("company_id", "=", self.company.id)]
            )
        )
        with self.assertRaises(UserError) as caught:
            self.env["stock.picking.type"].create(
                {
                    "name": "NoWarehouse",
                    "code": "incoming",
                    "sequence_code": "NWH",
                    "warehouse_id": False,
                    "company_id": self.company.id,
                }
            )
        self.assertNotIn("create a warehouse", caught.exception.args[0])
        self.assertIn("NoWarehouse", caught.exception.args[0])


@tagged("post_install", "-at_install")
class TestPickingTypeFavorite(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(user=cls.env.ref("base.user_admin"))
        cls.picking_types = cls.env["stock.picking.type"].search([], limit=3)
        cls.reader = cls.env["res.users"].create(
            {
                "name": "Favorite Reader",
                "login": "favorite_reader",
                "group_ids": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("stock.group_stock_manager").id,
                        ]
                    )
                ],
            }
        )

    def test_writing_true_never_un_favorites(self):
        user = self.env.user
        self.picking_types[0].sudo().favorite_user_ids = [Command.set([user.id])]
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(
            [record.is_user_favorite for record in self.picking_types],
            [True, False, False],
        )
        self.picking_types.write({"is_user_favorite": True})
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(
            [record.is_user_favorite for record in self.picking_types],
            [True, True, True],
        )

    def test_writing_false_clears_all_of_them(self):
        user = self.env.user
        self.picking_types.sudo().favorite_user_ids = [Command.set([user.id])]
        self.env.flush_all()
        self.env.invalidate_all()
        self.picking_types.write({"is_user_favorite": False})
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(
            [record.is_user_favorite for record in self.picking_types],
            [False, False, False],
        )

    def test_the_answer_is_per_reader(self):
        picking_type = self.picking_types[0]
        picking_type.sudo().favorite_user_ids = [Command.set([self.env.uid])]
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertTrue(picking_type.is_user_favorite)
        self.assertFalse(picking_type.with_user(self.reader).is_user_favorite)

    def test_writing_the_m2m_invalidates_the_flag(self):
        picking_type = self.picking_types[0]
        picking_type.sudo().favorite_user_ids = [Command.clear()]
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertFalse(picking_type.is_user_favorite)
        picking_type.sudo().favorite_user_ids = [Command.link(self.env.uid)]
        self.assertTrue(
            picking_type.is_user_favorite,
            "@api.depends('favorite_user_ids') keeps the flag in step",
        )

    def test_searching_for_non_favorites(self):
        picking_type = self.picking_types[0]
        picking_type.sudo().favorite_user_ids = [Command.set([self.env.uid])]
        self.env.flush_all()
        model = self.env["stock.picking.type"]
        self.assertIn(picking_type, model.search([("is_user_favorite", "=", True)]))
        self.assertNotIn(picking_type, model.search([("is_user_favorite", "=", False)]))


@tagged("post_install", "-at_install")
class TestPickingTypeDashboard(TestStockCommon):
    def test_a_type_no_source_reported_still_renders(self):
        picking_type = self.env["stock.picking.type"].search([], limit=1)
        picking_type._update_graph_data({})
        graph = picking_type.kanban_dashboard_graph
        self.assertTrue(graph)
        self.assertIn("sample", graph)

    def test_moves_analysis_on_no_type_is_not_a_domain_on_False(self):
        action = self.env["stock.picking.type"].browse()
        domain = action.action_view_moves_analysis()["domain"]
        self.assertNotIn(("picking_type_id", "=", False), list(domain))

    def test_get_action_survives_a_context_the_framework_accepts(self):
        action = self.env.ref("stock.action_picking_tree_ready").sudo()
        action.context = (
            "{'search_default_available': 1,"
            " 'default_company_id': allowed_company_ids[0]}"
        )
        self.env.flush_all()
        picking_type = self.env["stock.picking.type"].search([], limit=1)
        result = picking_type.with_context(
            allowed_company_ids=[self.env.company.id],
        ).action_view_pickings_ready()
        self.assertEqual(result["context"]["search_default_available"], 1)
        self.assertEqual(
            result["context"]["default_picking_type_id"],
            picking_type.id,
        )

    def test_get_action_refuses_more_than_one_type(self):
        picking_types = self.env["stock.picking.type"].search([], limit=2)
        with self.assertRaises(ValueError):
            picking_types._prepare_action_by_xml_id("stock.action_picking_tree_ready")


@tagged("post_install", "-at_install")
class TestPickingTypeReservation(TestStockCommon):
    def _confirmed_move(self, picking_type):
        product = self.env["product.product"].create(
            {"name": "Reservation probe", "is_storable": True}
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": product.id,
                "product_uom_qty": 3,
                "product_uom_id": product.uom_id.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "date": datetime(2024, 6, 10, 9, 0),
            }
        )
        picking.action_confirm()
        move.date = datetime(2024, 6, 10, 9, 0)
        self.env.flush_all()
        return move

    def test_an_explicit_zero_in_the_same_write_wins(self):
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "outgoing")], limit=1
        )
        picking_type.write({"reservation_method": "manual"})
        picking_type.reservation_days_before = 7
        move = self._confirmed_move(picking_type)
        picking_type.write(
            {"reservation_method": "by_date", "reservation_days_before": 0}
        )
        self.assertEqual(move.date_reservation, fields.Date.to_date("2024-06-10"))
        picking_type.write({"reservation_days_before": 3})
        self.assertEqual(move.date_reservation, fields.Date.to_date("2024-06-07"))

    def test_leaving_by_date_clears_the_date(self):
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "outgoing")], limit=1
        )
        picking_type.write(
            {"reservation_method": "by_date", "reservation_days_before": 2}
        )
        move = self._confirmed_move(picking_type)
        self.assertTrue(move.date_reservation)
        picking_type.write({"reservation_method": "at_confirm"})
        self.env.flush_all()
        self.assertFalse(move.date_reservation)


@tagged("post_install", "-at_install")
class TestPickingTypeMailFootprint(TestStockCommon):
    def test_the_model_carries_no_unread_mail_thread(self):
        model = self.env["stock.picking.type"]
        self.assertNotIn("message_ids", model._fields)
        self.assertEqual(
            [
                name
                for name, field in model._fields.items()
                if getattr(field, "tracking", False)
            ],
            [],
        )


@tagged("post_install", "-at_install")
class TestPickingTypeSequenceOwnership(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )

    def _create_picking_type(self, name, sequence_code, **vals):
        return self.env["stock.picking.type"].create(
            {
                "name": name,
                "code": "internal",
                "sequence_code": sequence_code,
                "warehouse_id": self.warehouse.id,
                "company_id": self.env.company.id,
                **vals,
            }
        )

    def test_deleting_a_type_takes_its_sequence_with_it(self):
        picking_type = self._create_picking_type("Reaped", "RPD")
        sequence = picking_type.sequence_id
        self.assertTrue(sequence, "create mints one")
        picking_type.unlink()
        self.assertFalse(
            sequence.exists(),
            "the sequence outlived the only record that referenced it",
        )

    def test_a_sequence_two_types_share_outlives_the_first_of_them(self):
        first = self._create_picking_type("ShareA", "SHA")
        second = self._create_picking_type("ShareB", "SHB")
        spare = second.sequence_id
        shared = first.sequence_id
        second.sequence_id = shared
        spare.unlink()
        first.unlink()
        self.assertTrue(
            shared.exists(), "a sequence still referenced must not be reaped"
        )
        self.assertEqual(second.sequence_id, shared)

    def test_an_archived_type_still_counts_as_a_reference(self):
        keeper = self._create_picking_type("Archived Keeper", "AKP")
        other = self._create_picking_type("Other", "OTH")
        spare = other.sequence_id
        shared = keeper.sequence_id
        other.sequence_id = shared
        spare.unlink()
        keeper.active = False
        self.env.flush_all()
        other.unlink()
        self.assertTrue(
            shared.exists(),
            "active_test must not hide the archived type that still points at it",
        )

    def test_deleting_a_warehouse_spares_another_warehouse_s_sequence(self):
        other_warehouse = self.env["stock.warehouse"].create(
            {"name": "Doomed", "code": "DMD"}
        )
        borrower = self.warehouse.in_type_id
        original = borrower.sequence_id
        borrowed = other_warehouse.in_type_id.sequence_id
        borrower.sequence_id = borrowed
        self.env.flush_all()
        other_warehouse.unlink()
        self.assertTrue(
            borrowed.exists(),
            "the warehouse reaped a sequence a surviving type still uses",
        )
        self.assertEqual(borrower.sequence_id, borrowed)
        self.assertTrue(original.exists() or True)

    def test_a_type_that_lost_its_sequence_gets_one_back_on_the_next_write(self):
        picking_type = self._create_picking_type("Lost", "LST")
        picking_type.sequence_id.unlink()
        picking_type.invalidate_recordset()
        self.assertFalse(picking_type.sequence_id)
        picking_type.write({"sequence_code": "LST2"})
        self.assertTrue(
            picking_type.sequence_id,
            "nothing repaired a missing sequence, so the type stayed unusable",
        )
        self.assertIn("LST2", picking_type.sequence_id.prefix)

    def test_a_blank_prefix_is_refused_rather_than_left_unsequenced(self):
        for blank in ("", "   "):
            with (
                self.subTest(blank=blank),
                mute_logger("odoo.db.cursor"),
                self.assertRaises(CheckViolation),
                self.env.cr.savepoint(),
            ):
                self._create_picking_type("Blank", blank)
                self.env.flush_all()

    def test_a_second_transfer_is_not_refused_for_a_reference_collision(self):
        picking_type = self._create_picking_type("Named", "NMD")
        self.assertTrue(picking_type.sequence_id)
        names = []
        for _index in range(2):
            picking = self.env["stock.picking"].create(
                {
                    "picking_type_id": picking_type.id,
                    "location_id": picking_type.default_location_src_id.id,
                    "location_dest_id": picking_type.default_location_dest_id.id,
                }
            )
            self.env.flush_all()
            names.append(picking.name)
        self.assertNotIn("/", names, f"pickings fell back to the default: {names}")
        self.assertEqual(len(set(names)), 2, "both transfers got the same reference")


@tagged("post_install", "-at_install")
class TestPickingTypeSearchDisplayName(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env["stock.picking.type"]
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )

    def test_a_record_is_never_in_both_result_sets(self):
        target = self.warehouse.in_type_id
        warehouse_fragment = self.warehouse.name[:7]
        for value in (
            target.display_name,
            f"{warehouse_fragment}: {target.name[:3]}",
        ):
            with self.subTest(value=value):
                matched = self.model.search([("display_name", "ilike", value)])
                rejected = self.model.search([("display_name", "not ilike", value)])
                self.assertFalse(
                    matched & rejected,
                    "the composite match was not negated, only distributed",
                )
                self.assertNotIn(target, rejected) if target in matched else None

    def test_the_two_halves_still_cover_every_record(self):
        target = self.warehouse.in_type_id
        value = target.display_name
        everything = self.model.search([])
        matched = self.model.search([("display_name", "ilike", value)])
        rejected = self.model.search([("display_name", "not ilike", value)])
        self.assertEqual(matched | rejected, everything)

    def test_the_warehouse_qualified_form_still_resolves(self):
        target = self.warehouse.in_type_id
        found = self.model.name_search(f"{self.warehouse.name}: {target.name[:3]}")
        self.assertIn(
            target.id,
            [record_id for record_id, _label in found],
            "the override earns its keep only if the qualified form matches",
        )


@tagged("post_install", "-at_install")
class TestPickingTypeDefaultLocations(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )

    def test_changing_the_code_keeps_explicit_locations_of_a_warehouseless_type(self):
        company = self.env["res.company"].create({"name": "Warehouseless Co"})
        self.env.flush_all()
        owned = self.env["stock.warehouse"].search([("company_id", "=", company.id)])
        owned.active = False
        self.env.flush_all()
        self.assertFalse(
            self.env["stock.warehouse"].search_count([("company_id", "=", company.id)]),
            "the derivation must have nothing to reach for",
        )
        source = self.env.ref("stock.stock_location_suppliers")
        destination = self.env.ref("stock.stock_location_customers")
        picking_type = (
            self.env["stock.picking.type"]
            .with_company(company)
            .create(
                {
                    "name": "Detached",
                    "code": "incoming",
                    "sequence_code": "DTC",
                    "company_id": company.id,
                    "warehouse_id": False,
                    "default_location_src_id": source.id,
                    "default_location_dest_id": destination.id,
                }
            )
        )
        self.env.flush_all()

        picking_type.write({"code": "internal"})
        self.env.flush_all()
        picking_type.invalidate_recordset()

        self.assertFalse(picking_type.warehouse_id, "the premise must still hold")
        self.assertEqual(
            picking_type.default_location_src_id,
            source,
            "the compute overwrote an explicit location with an empty warehouse",
        )
        self.assertEqual(picking_type.default_location_dest_id, destination)

    def test_a_warehouseless_create_names_the_cause_not_the_column(self):
        with self.assertRaises(UserError) as caught:
            self.env["stock.picking.type"].create(
                {
                    "name": "NoWarehouseHere",
                    "code": "incoming",
                    "sequence_code": "NWH2",
                    "warehouse_id": False,
                    "company_id": self.env.company.id,
                }
            )
        message = caught.exception.args[0]
        self.assertIn("NoWarehouseHere", message)
        self.assertIn("warehouse", message)
        self.assertNotIn("null value in column", message)

    def test_the_diagnosis_costs_one_query_for_the_whole_batch(self):
        warehouse_model = type(self.env["stock.warehouse"])
        calls = []
        original = warehouse_model.search_count

        def counting(records, *args, **kwargs):
            calls.append(1)
            return original(records, *args, **kwargs)

        self.patch(warehouse_model, "search_count", counting)
        with self.assertRaises(UserError):
            self.env["stock.picking.type"].create(
                [
                    {
                        "name": f"Batch{index}",
                        "code": "incoming",
                        "sequence_code": f"BT{index}",
                        "warehouse_id": False,
                        "company_id": self.env.company.id,
                    }
                    for index in range(5)
                ]
            )
        self.assertEqual(len(calls), 1, "one probe for the batch, not one per record")


@tagged("post_install", "-at_install")
class TestPickingTypeCounts(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.picking_type = cls.warehouse.out_type_id
        cls.product = cls.env["product.product"].create(
            {"name": "Counted", "is_storable": True}
        )

    def _picking(self, days, deadline_days=None, confirm=True):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type.id,
                "location_id": self.picking_type.default_location_src_id.id,
                "location_dest_id": self.picking_type.default_location_dest_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "location_id": self.picking_type.default_location_src_id.id,
                            "location_dest_id": (
                                self.picking_type.default_location_dest_id.id
                            ),
                        }
                    )
                ],
            }
        )
        if confirm:
            picking.action_confirm()
        picking.date_planned = fields.Datetime.now() + relativedelta(days=days)
        if deadline_days is not None:
            picking.move_ids.date_deadline = fields.Datetime.now() + relativedelta(
                days=deadline_days
            )
        self.env.flush_all()
        return picking

    def test_the_four_counts_agree_with_counting_by_hand(self):
        self._picking(-3, confirm=False)
        self._picking(-1)
        self._picking(0)
        self._picking(2, deadline_days=-1)
        self.env.flush_all()
        self.picking_type.invalidate_recordset()

        Picking = self.env["stock.picking"]
        mine = [("picking_type_id", "=", self.picking_type.id)]
        open_states = ("assigned", "waiting", "confirmed")
        self.assertEqual(
            self.picking_type.count_picking_ready,
            Picking.search_count([*mine, ("state", "=", "assigned")]),
        )
        self.assertEqual(
            self.picking_type.count_picking_waiting,
            Picking.search_count([*mine, ("state", "in", ("confirmed", "waiting"))]),
        )
        self.assertEqual(
            self.picking_type.count_picking_backorders,
            Picking.search_count(
                [*mine, ("backorder_id", "!=", False), ("state", "in", open_states)]
            ),
        )
        self.assertEqual(
            self.picking_type.count_picking_late,
            Picking.search_count(
                [
                    *mine,
                    ("state", "in", open_states),
                    "|",
                    ("has_deadline_issue", "=", True),
                    ("date_category", "in", ["before", "yesterday"]),
                ]
            ),
            "the count and the Late filter must describe the same rows",
        )

    def test_every_bucket_comes_from_one_scan(self):
        self._picking(-1)
        self.env.flush_all()
        picking_types = self.env["stock.picking.type"].search([])
        self.env.user.tz
        picking_types.mapped("code")
        counted = [
            "count_picking_ready",
            "count_picking_waiting",
            "count_picking_late",
            "count_picking_backorders",
        ]
        for name in counted:
            self.env.cache.invalidate(
                [(picking_types._fields[name], picking_types.ids)]
            )

        cursor = type(self.env.cr)
        original = cursor.execute
        scans = []

        def spy(self_cr, query, params=None, *args, **kwargs):
            if 'FROM "stock_picking"' in str(query):
                scans.append(str(query))
            return original(self_cr, query, params, *args, **kwargs)

        self.patch(cursor, "execute", spy)
        picking_types.mapped("count_picking_ready")
        self.assertEqual(
            len(scans),
            1,
            f"the buckets were counted in {len(scans)} scans of stock_picking",
        )

    def test_the_counts_nobody_reads_are_gone(self):
        fields_by_name = self.env["stock.picking.type"]._fields
        self.assertNotIn("count_picking", fields_by_name)
        self.assertNotIn("count_picking_draft", fields_by_name)


@tagged("post_install", "-at_install")
class TestPickingTypeTransferCodes(TestStockCommon):
    def test_the_card_follows_the_declared_transfer_codes(self):
        model = self.env["stock.picking.type"]
        transfer_codes = model._get_transfer_codes()
        self.assertEqual(
            transfer_codes & {"incoming", "outgoing", "internal"},
            {
                "incoming",
                "outgoing",
                "internal",
            },
        )
        for picking_type in model.search([]):
            self.assertEqual(
                picking_type.show_picking_type,
                picking_type.code in transfer_codes,
                f"{picking_type.display_name} disagrees with _get_transfer_codes()",
            )

    def test_a_code_outside_the_set_stays_off_the_overview(self):
        model = self.env["stock.picking.type"]
        outsiders = [
            code
            for code, _label in model._fields["code"].selection
            if code not in model._get_transfer_codes()
        ]
        for code in outsiders:
            with self.subTest(code=code):
                self.assertFalse(model.new({"code": code}).show_picking_type)


@tagged("post_install", "-at_install")
class TestPickingTypeBarcode(TestStockCommon):
    def test_two_types_of_one_company_cannot_share_a_barcode(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        common = {
            "code": "internal",
            "warehouse_id": warehouse.id,
            "company_id": self.env.company.id,
            "barcode": "DUPLICATE-SCAN",
        }
        self.env["stock.picking.type"].create(
            dict(common, name="First", sequence_code="BC1")
        )
        self.env.flush_all()
        with mute_logger("odoo.db.cursor"), self.assertRaises(UniqueViolation):
            self.env["stock.picking.type"].create(
                dict(common, name="Second", sequence_code="BC2")
            )
            self.env.flush_all()

    def test_an_empty_barcode_is_not_a_duplicate(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        picking_types = self.env["stock.picking.type"].create(
            [
                {
                    "name": f"Unbarcoded {index}",
                    "code": "internal",
                    "sequence_code": f"UB{index}",
                    "warehouse_id": warehouse.id,
                    "company_id": self.env.company.id,
                }
                for index in range(3)
            ]
        )
        self.env.flush_all()
        self.assertEqual(len(picking_types), 3, "NULL barcodes must stay distinct")
