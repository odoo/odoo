from contextlib import nullcontext
from datetime import timedelta
from unittest.mock import patch

from odoo import SUPERUSER_ID, fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged

from odoo.addons.stock.models.stock_orderpoint_replenish import (
    StockWarehouseOrderpointReplenish,
)
from odoo.addons.stock.models.stock_rule_selection import StockRuleSelection
from odoo.addons.stock.tests.common import is_module_installed


class TestAuditRuleResolution(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.category = cls.env["product.category"].create({"name": "Audit Categ"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Audit Resolution Product",
                "is_storable": True,
                "categ_id": cls.category.id,
            },
        )

    def _create_route_with_rules(self, name, sequence, push_dest, pull_src):
        route = self.env["stock.route"].create(
            {
                "name": name,
                "sequence": sequence,
                "product_selectable": True,
                "product_categ_selectable": True,
            },
        )
        push_rule = self.env["stock.rule"].create(
            {
                "name": f"{name} push",
                "route_id": route.id,
                "action": "push",
                "location_src_id": self.stock_location.id,
                "location_dest_id": push_dest.id,
                "picking_type_id": self.warehouse.int_type_id.id,
            },
        )
        pull_rule = self.env["stock.rule"].create(
            {
                "name": f"{name} pull",
                "route_id": route.id,
                "action": "pull",
                "location_src_id": pull_src.id,
                "location_dest_id": self.stock_location.id,
                "procure_method": "make_to_stock",
                "picking_type_id": self.warehouse.in_type_id.id,
            },
        )
        return route, push_rule, pull_rule

    def test_push_and_pull_prefer_product_route(self):
        dest_a = self.env["stock.location"].create(
            {"name": "Audit Dest A", "location_id": self.stock_location.id},
        )
        dest_b = self.env["stock.location"].create(
            {"name": "Audit Dest B", "location_id": self.stock_location.id},
        )
        categ_route, _categ_push, _categ_pull = self._create_route_with_rules(
            "Audit Category Route",
            1,
            dest_a,
            self.supplier_location,
        )
        product_route, product_push, product_pull = self._create_route_with_rules(
            "Audit Product Route",
            20,
            dest_b,
            self.supplier_location,
        )
        self.category.route_ids = [Command.link(categ_route.id)]
        self.product.route_ids = [Command.link(product_route.id)]

        pull_rule = self.env["stock.rule"]._get_rule(
            self.product,
            self.stock_location,
            {"warehouse_id": self.warehouse},
        )
        push_rule = self.env["stock.rule"]._get_push_rule(
            self.product,
            self.stock_location,
            {"warehouse_id": self.warehouse},
        )
        self.assertEqual(
            pull_rule,
            product_pull,
            "Pull resolution must prefer the product-specific route over the "
            "category route regardless of route sequence.",
        )
        self.assertEqual(
            push_rule,
            product_push,
            "Push resolution must use the same intra-bucket ordering as pull "
            "resolution (product routes first) instead of raw route sequence.",
        )

    def test_run_hoists_rule_dict_across_procurements(self):
        route = self.warehouse.reception_route_id
        self.env["stock.rule"].create(
            {
                "name": "Audit supplier pull",
                "route_id": route.id,
                "action": "pull",
                "location_src_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "procure_method": "make_to_stock",
                "picking_type_id": self.warehouse.in_type_id.id,
            },
        )
        products = self.env["product.product"].create(
            [
                {
                    "name": f"Audit Group Product {i}",
                    "is_storable": True,
                    "categ_id": self.category.id,
                }
                for i in range(3)
            ],
        )
        Procurement = self.env["stock.rule"].Procurement
        procurements = [
            Procurement(
                product,
                4.0,
                product.uom_id,
                self.stock_location,
                product.name,
                "audit group test",
                self.env.company,
                {"warehouse_id": self.warehouse, "route_ids": route},
            )
            for product in products
        ]

        original = StockRuleSelection._get_rule_candidates
        calls = []

        def counting(rule_model, *args, **kwargs):
            calls.append(1)
            return original(rule_model, *args, **kwargs)

        with patch.object(StockRuleSelection, "_get_rule_candidates", counting):
            self.env["stock.rule"].run(procurements)

        self.assertEqual(
            len(calls),
            1,
            "Three procurements sharing (root, company, warehouse, route set) "
            "must share a single prefetched rule dict.",
        )
        moves = self.env["stock.move"].search(
            [("product_id", "in", products.ids), ("origin", "=", "audit group test")],
        )
        self.assertEqual(len(moves), 3)
        self.assertEqual(
            set(moves.mapped("location_id.id")), {self.supplier_location.id}
        )


class TestAuditOrderpointFixes(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.product = cls.env["product.product"].create(
            {"name": "Audit Orderpoint Product", "is_storable": True},
        )

    def _add_supplier_rule(self):
        self.env["stock.rule"].create(
            {
                "name": "Audit Rule Supplier",
                "route_id": self.warehouse.reception_route_id.id,
                "location_dest_id": self.stock_location.id,
                "location_src_id": self.supplier_location.id,
                "action": "pull",
                "procure_method": "make_to_stock",
                "picking_type_id": self.warehouse.in_type_id.id,
            },
        )

    def test_force_to_max_survives_intervening_flush(self):
        self._add_supplier_rule()
        self.env["stock.quant"]._update_available_quantity(
            self.product,
            self.stock_location,
            10,
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "product_min_qty": 5,
                "product_max_qty": 200,
                "route_id": self.warehouse.reception_route_id.id,
            },
        )
        self.assertEqual(orderpoint.qty_forecast, 10.0)

        original = StockWarehouseOrderpointReplenish._prepare_procurement_vals

        def flushing(orderpoint_record, date=False):
            orderpoint_record.env.flush_all()
            return original(orderpoint_record, date=date)

        with patch.object(
            StockWarehouseOrderpointReplenish,
            "_prepare_procurement_vals",
            flushing,
        ):
            orderpoint.action_replenish(force_to_max=True)

        self.assertEqual(
            orderpoint.qty_forecast,
            200.0,
            "The forced-to-max quantity must be procured even when a flush "
            "runs between the forcing and the procurement construction.",
        )

    def test_qty_to_order_explicit_zero_sticks(self):
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "trigger": "manual",
                "product_min_qty": 5,
                "product_max_qty": 10,
            },
        )
        self.assertEqual(
            orderpoint.qty_to_order,
            10.0,
            "Sanity: with no stock the suggestion is product_max_qty.",
        )
        orderpoint.qty_to_order = 0
        self.env.flush_all()
        self.assertEqual(orderpoint.qty_to_order, 0.0)
        orderpoint.invalidate_recordset()
        self.assertEqual(
            orderpoint.qty_to_order,
            0.0,
            "The explicit 0 must survive a cache invalidation/recompute.",
        )
        positive = self.env["stock.warehouse.orderpoint"].search(
            [("qty_to_order", ">", 0)],
        )
        self.assertNotIn(orderpoint, positive)
        zeroed = self.env["stock.warehouse.orderpoint"].search(
            [("qty_to_order", "=", 0)],
        )
        self.assertIn(orderpoint, zeroed)
        orderpoint.qty_to_order = 4
        self.env.flush_all()
        self.assertEqual(orderpoint.qty_to_order, 4.0)
        self.assertTrue(
            orderpoint.qty_to_order_manual_set,
            "4 differs from the suggestion, so it is an override like any other -- "
            "the flag records that one exists, not that it is zero.",
        )
        orderpoint.qty_to_order = 0
        self.env.flush_all()
        orderpoint.action_remove_manual_qty_to_order()
        self.assertEqual(orderpoint.qty_to_order, 10.0)

    def test_qty_to_order_onchange_reflects_the_live_suggestion(self):
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "trigger": "manual",
                "product_min_qty": 5,
                "product_max_qty": 10,
            },
        )
        self.assertEqual(orderpoint.qty_to_order, 10.0)
        spec = {
            name: {}
            for name in (
                "product_id",
                "location_id",
                "trigger",
                "product_min_qty",
                "product_max_qty",
                "qty_to_order",
            )
        }
        values = {
            name: (value[0] if isinstance(value, tuple) else value)
            for name, value in orderpoint.read(list(spec))[0].items()
            if name != "id"
        }
        echoed = orderpoint.onchange(
            dict(values, product_min_qty=8),
            ["product_min_qty"],
            spec,
        )["value"]
        self.assertNotEqual(
            echoed.get("qty_to_order", 10.0),
            0.0,
            "An unsaved record carries a NewId, which is falsy. A suggestion that "
            "filters on `orderpoint.id` therefore answers 0 for every row the user "
            "is still editing, and the web client renders that 0 in the To Order "
            "cell until the row is saved.",
        )
        orderpoint.write({"product_min_qty": 8, "qty_to_order": 10.0})
        self.env.flush_all()
        self.assertFalse(
            orderpoint.qty_to_order_manual_set,
            "A value that equals the live suggestion is not an override, whatever "
            "else the same write touches.",
        )
        self.assertEqual(orderpoint.qty_to_order, 10.0)

    def test_an_explicit_zero_survives_a_source_field_in_the_same_write(self):
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "trigger": "manual",
                "product_min_qty": 5,
                "product_max_qty": 10,
            },
        )
        orderpoint.write({"product_min_qty": 8, "qty_to_order": 0.0})
        self.env.flush_all()
        self.assertTrue(
            orderpoint.qty_to_order_manual_set,
            "0 differs from the suggestion, so it is an override. The heuristic "
            "that used to drop it could not tell a typed zero from a stale echo.",
        )
        self.assertEqual(orderpoint.qty_to_order, 0.0)

    def test_compute_qty_to_order_computed_is_batched(self):
        products = self.env["product.product"].create(
            [
                {"name": f"Audit Batch Product {i}", "is_storable": True}
                for i in range(3)
            ],
        )
        orderpoints = self.env["stock.warehouse.orderpoint"].create(
            [
                {
                    "product_id": product.id,
                    "product_min_qty": 1,
                    "product_max_qty": 7,
                }
                for product in products
            ],
        )
        self.env.flush_all()
        self.env.invalidate_all()

        in_progress_calls = []
        original = StockWarehouseOrderpointReplenish._get_quantity_in_progress

        def recording(records):
            in_progress_calls.append(len(records))
            return original(records)

        self.patch(
            StockWarehouseOrderpointReplenish, "_get_quantity_in_progress", recording
        )
        # the count is stock's own; purchase_stock adds its vendor lookups
        counted = (
            nullcontext()
            if is_module_installed(self.env, "purchase_stock")
            else self.assertQueryCount(__system__=17)
        )
        with counted:
            orderpoints._compute_qty_to_order_computed()

        self.assertEqual(
            in_progress_calls,
            [3],
            "One `_get_quantity_in_progress()` for the whole set, not one per record "
            "and not one for the shortage test plus another for the quantity.",
        )
        for orderpoint in orderpoints:
            self.assertEqual(orderpoint.qty_to_order_computed, 7.0)

    def test_lead_time_stats_exclude_immediate_receipts(self):
        def create_done_receipt(span):
            picking = self.env["stock.picking"].create(
                {
                    "picking_type_id": self.warehouse.in_type_id.id,
                    "location_id": self.supplier_location.id,
                    "location_dest_id": self.stock_location.id,
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_uom_qty": 5,
                                "product_uom_id": self.product.uom_id.id,
                                "location_id": self.supplier_location.id,
                                "location_dest_id": self.stock_location.id,
                            },
                        ),
                    ],
                },
            )
            picking.action_confirm()
            picking.move_ids.quantity = 5
            picking.move_ids.picked = True
            picking.button_validate()
            self.env.flush_all()
            date_done = fields.Datetime.now()
            self.env.cr.execute(
                "UPDATE stock_picking SET create_date = %s, date_done = %s"
                " WHERE id = %s",
                (date_done - span, date_done, picking.id),
            )
            return picking

        create_done_receipt(timedelta(minutes=10))
        create_done_receipt(timedelta(days=5))

        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "product_min_qty": 1,
                "product_max_qty": 5,
            },
        )
        orderpoint._compute_lead_time_stats()
        self.assertEqual(
            orderpoint.lead_time_sample_count,
            1,
            "The sub-hour receipt must be excluded from the sampling.",
        )
        self.assertAlmostEqual(orderpoint.actual_lead_time_avg, 5.0, places=2)

    def test_report_attributes_sublocation_shortage(self):
        shelf = self.env["stock.location"].create(
            {
                "name": "Audit Shelf",
                "usage": "internal",
                "location_id": self.stock_location.id,
            },
        )
        out_move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "product_uom_qty": 5.0,
                "location_id": shelf.id,
                "location_dest_id": self.customer_location.id,
            },
        )
        out_move._action_confirm()
        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [
                ("product_id", "=", self.product.id),
                ("location_id", "=", self.stock_location.id),
            ],
        )
        self.assertTrue(
            orderpoint,
            "The sub-location shortage must be attributed to the replenish "
            "ancestor location.",
        )
        self.assertTrue(orderpoint.is_autogenerated)
        self.assertEqual(orderpoint.trigger, "manual")

    def test_autovacuum_keyed_on_is_autogenerated(self):
        Orderpoint = self.env["stock.warehouse.orderpoint"]
        admin_manual = Orderpoint.with_user(SUPERUSER_ID).create(
            {
                "product_id": self.product.id,
                "trigger": "manual",
                "product_min_qty": 0,
                "product_max_qty": 0,
            },
        )
        autogenerated_vals = Orderpoint._prepare_orderpoint_vals(
            self.product.id,
            self.warehouse.wh_input_stock_loc_id.id,
        )
        autogenerated = Orderpoint.with_user(SUPERUSER_ID).create(
            dict(autogenerated_vals, warehouse_id=self.warehouse.id),
        )
        self.assertTrue(autogenerated.is_autogenerated)
        removed = (admin_manual | autogenerated)._remove_processed_orderpoints()
        self.assertEqual(
            removed,
            autogenerated,
            "Only the autogenerated orderpoint may be vacuumed; the "
            "admin-created manual one must survive.",
        )
        self.assertTrue(admin_manual.exists())
        self.assertFalse(autogenerated.exists())

    def test_search_effective_route_id_name_operator(self):
        route = self.warehouse.reception_route_id
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "product_min_qty": 1,
                "product_max_qty": 5,
                "route_id": route.id,
            },
        )
        found = self.env["stock.warehouse.orderpoint"].search(
            [("effective_route_id", "ilike", route.name)],
        )
        self.assertIn(orderpoint, found)
        found_by_id = self.env["stock.warehouse.orderpoint"].search(
            [("effective_route_id", "in", route.ids)],
        )
        self.assertIn(orderpoint, found_by_id)


class TestAuditTopologyFixes(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )

    def test_archive_ancestor_of_warehouse_stock_blocked(self):
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Audit Zone WH", "code": "AZWH"},
        )
        zone = self.env["stock.location"].create(
            {
                "name": "Audit Zone",
                "usage": "view",
                "location_id": warehouse.view_location_id.id,
            },
        )
        warehouse.lot_stock_id.location_id = zone
        with self.assertRaises(UserError):
            zone.action_archive()
        self.assertTrue(warehouse.lot_stock_id.active)

    def test_unlink_location_with_descendants_guarded(self):
        parent = self.env["stock.location"].create(
            {
                "name": "Audit Unlink Parent",
                "usage": "internal",
                "location_id": self.warehouse.lot_stock_id.id,
            },
        )
        child = self.env["stock.location"].create(
            {
                "name": "Audit Unlink Child",
                "usage": "internal",
                "location_id": parent.id,
            },
        )
        child.action_archive()
        with self.assertRaises(UserError):
            parent.unlink()
        self.assertTrue(parent.exists())
        self.assertTrue(child.exists())
        parent.with_context(stock_unlink_subtree=True).unlink()
        self.assertFalse(parent.exists())
        self.assertFalse(child.exists())

    def test_settings_compute_replenish_on_order_without_mto(self):
        route = self.env.ref("stock.route_warehouse0_mto", raise_if_not_found=False)
        if route:
            route.sudo().unlink()
        settings = self.env["res.config.settings"].new({})
        self.assertFalse(settings.replenish_on_order)

    def test_route_unarchive_realigns_resupply_legs(self):
        supplier_wh = self.env["stock.warehouse"].create(
            {
                "name": "Audit Supplier WH",
                "code": "ASWH",
                "delivery_steps": "pick_ship",
            },
        )
        supplied_wh = self.env["stock.warehouse"].create(
            {
                "name": "Audit Supplied WH",
                "code": "ADWH",
                "resupply_wh_ids": [Command.set(supplier_wh.ids)],
            },
        )
        resupply_route = self.env["stock.route"].search(
            [
                ("supplied_wh_id", "=", supplied_wh.id),
                ("supplier_wh_id", "=", supplier_wh.id),
            ],
        )
        self.assertTrue(resupply_route)
        pick_leg = (
            self.env["stock.rule"]
            .with_context(active_test=False)
            .search(
                [
                    ("route_id", "=", resupply_route.id),
                    ("action", "!=", "push"),
                    (
                        "location_dest_id",
                        "=",
                        supplier_wh.wh_output_stock_loc_id.id,
                    ),
                    ("picking_type_id", "=", supplier_wh.pick_type_id.id),
                ],
            )
        )
        self.assertTrue(pick_leg.active, "Multi-step delivery: pick leg active.")
        supplier_wh.delivery_steps = "ship_only"
        self.assertFalse(pick_leg.active)
        resupply_route.action_archive()
        resupply_route.action_unarchive()
        self.assertFalse(
            pick_leg.active,
            "Unarchiving the resupply route must re-align the step-dependent "
            "legs with the supplier's current (single-step) delivery config.",
        )

    def test_replenish_mixin_excludes_intercompany_routes(self):
        inter_company_location = self.env.ref("stock.stock_location_inter_company")
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        stock_location = self.warehouse.lot_stock_id

        def create_route(name, extra_rule_vals=None):
            route = self.env["stock.route"].create(
                {"name": name, "product_selectable": True},
            )
            self.env["stock.rule"].create(
                {
                    "name": f"{name} pull",
                    "route_id": route.id,
                    "action": "pull",
                    "location_src_id": supplier_location.id,
                    "location_dest_id": stock_location.id,
                    "procure_method": "make_to_stock",
                    "picking_type_id": self.warehouse.in_type_id.id,
                },
            )
            if extra_rule_vals:
                self.env["stock.rule"].create(
                    dict(
                        {
                            "name": f"{name} intercomp",
                            "route_id": route.id,
                            "action": "pull",
                            "procure_method": "make_to_stock",
                            "picking_type_id": self.warehouse.int_type_id.id,
                        },
                        **extra_rule_vals,
                    ),
                )
            return route

        clean_route = create_route("Audit Clean Route")
        intercomp_route = create_route(
            "Audit Intercomp Route",
            {
                "location_src_id": inter_company_location.id,
                "location_dest_id": stock_location.id,
            },
        )
        product = self.env["product.product"].create(
            {"name": "Audit Mixin Product", "is_storable": True},
        )
        wizard = self.env["product.replenish"].new(
            {
                "product_id": product.id,
                "product_tmpl_id": product.product_tmpl_id.id,
                "warehouse_id": self.warehouse.id,
            },
        )
        allowed = self.env["stock.route"].search(wizard._get_domain_allowed_route())
        self.assertIn(clean_route, allowed)
        self.assertNotIn(
            intercomp_route,
            allowed,
            "A route with a rule sourcing from the inter-company location "
            "must be excluded from the replenish wizard's allowed routes.",
        )


@tagged("post_install", "-at_install")
class TestAuditProcureMultiCompany(TransactionCase):
    def test_deadline_date_other_company(self):
        customer_location = self.env.ref("stock.stock_location_customers")
        company_b = self.env["res.company"].create({"name": "Audit Deadline Co"})
        warehouse_b = (
            self.env["stock.warehouse"]
            .sudo()
            .search([("company_id", "=", company_b.id)], limit=1)
        )
        if not warehouse_b:
            warehouse_b = company_b.sudo()._create_warehouse()
        product = (
            self.env["product.product"]
            .sudo()
            .create(
                {
                    "name": "Audit Deadline Product",
                    "is_storable": True,
                    "company_id": False,
                },
            )
        )
        self.env["stock.quant"].sudo()._update_available_quantity(
            product,
            warehouse_b.lot_stock_id,
            10,
        )
        orderpoint = (
            self.env["stock.warehouse.orderpoint"]
            .sudo()
            .with_company(company_b)
            .create(
                {
                    "product_id": product.id,
                    "company_id": company_b.id,
                    "warehouse_id": warehouse_b.id,
                    "location_id": warehouse_b.lot_stock_id.id,
                    "product_min_qty": 5,
                    "product_max_qty": 20,
                },
            )
        )
        out_move = (
            self.env["stock.move"]
            .sudo()
            .with_company(company_b)
            .create(
                {
                    "product_id": product.id,
                    "product_uom_id": product.uom_id.id,
                    "product_uom_qty": 8.0,
                    "location_id": warehouse_b.lot_stock_id.id,
                    "location_dest_id": customer_location.id,
                    "company_id": company_b.id,
                    "date": fields.Datetime.now() + timedelta(days=3),
                },
            )
        )
        out_move._action_confirm()

        orderpoint_ambient = orderpoint.with_context(
            allowed_company_ids=[self.env.company.id],
        )
        orderpoint_ambient._compute_deadline_date()
        expected = (
            fields.Date.today()
            + timedelta(days=3)
            - timedelta(days=int(orderpoint.lead_days))
        )
        self.assertEqual(
            orderpoint.deadline_date,
            expected,
            "A company-B orderpoint must see company-B moves even when the "
            "ambient companies don't include company B.",
        )

    def test_create_warehouse_idempotent_with_archived(self):
        company = self.env["res.company"].create({"name": "Audit Dedup Co"})
        warehouse = company.sudo()._create_warehouse()
        self.assertTrue(warehouse)
        warehouse.action_archive()
        result = company.sudo()._create_warehouse()
        self.assertEqual(
            result,
            warehouse,
            "The archived warehouse must be reused, not shadowed by a "
            "duplicate that violates unique(name, company_id).",
        )
