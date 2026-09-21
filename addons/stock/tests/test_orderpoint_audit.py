import logging
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestOrderpointAudit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Orderpoint = cls.env["stock.warehouse.orderpoint"]
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.customers = cls.env.ref("stock.stock_location_customers")
        cls.suppliers = cls.env.ref("stock.stock_location_suppliers")
        cls.vendor = cls.env["res.partner"].create({"name": "Audit Vendor"})
        cls.supply_route = cls.env["stock.route"].create(
            {
                "name": "Audit Supply",
                "product_selectable": True,
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Audit: Vendors -> Stock",
                            "action": "pull",
                            "procure_method": "make_to_stock",
                            "picking_type_id": cls._incoming_picking_type().id,
                            "location_src_id": cls.suppliers.id,
                            "location_dest_id": cls.stock_location.id,
                        },
                    ),
                ],
            },
        )

    @classmethod
    def _incoming_picking_type(cls):
        return cls.env["stock.picking.type"].search(
            [("code", "=", "incoming"), ("warehouse_id", "=", cls.warehouse.id)],
            limit=1,
        )

    def _product(self, name, suppliable=True):
        values = {"name": name, "is_storable": True}
        if suppliable:
            values["seller_ids"] = [
                (0, 0, {"partner_id": self.vendor.id, "min_qty": 0, "price": 1}),
            ]
            values["route_ids"] = [(6, 0, self.supply_route.ids)]
        return self.env["product.product"].create(values)

    def _unsuppliable_location(self, name):
        root = self.env["stock.location"].create(
            {"name": f"{name} Root", "usage": "view", "location_id": False},
        )
        return self.env["stock.location"].create(
            {"name": name, "usage": "internal", "location_id": root.id},
        )

    def _orderpoint(self, product, **overrides):
        values = {
            "product_id": product.id,
            "location_id": self.stock_location.id,
            "warehouse_id": self.warehouse.id,
            "product_min_qty": 10,
            "product_max_qty": 10,
            "trigger": "manual",
        }
        values.update(overrides)
        return self.Orderpoint.create(values)

    def _outgoing(self, product, quantity, days_out):
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": quantity,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customers.id,
                "date": fields.Datetime.now() + timedelta(days=days_out),
            },
        )
        move._action_confirm()
        return move

    def _done_receipt(self, product, lead_days):
        picking_type = self._incoming_picking_type()
        picking = self.env["stock.picking"].create(
            {"picking_type_id": picking_type.id},
        )
        self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": product.id,
                "product_uom_qty": 10,
                "location_id": self.suppliers.id,
                "location_dest_id": picking.location_dest_id.id,
            },
        )
        picking.action_confirm()
        picking.move_ids.quantity = 10
        picking.button_validate()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE stock_picking SET create_date = date_done - %s::interval "
            "WHERE id = %s",
            (f"{lead_days} days", picking.id),
        )
        self.env.invalidate_all()
        return picking

    def test_replenishing_does_not_mute_a_manual_orderpoint(self):
        product = self._product("Audit Mute")
        orderpoint = self._orderpoint(product, route_id=self.supply_route.id)
        self.env.flush_all()
        self.assertEqual(orderpoint.qty_to_order, 10.0)

        orderpoint.action_replenish()
        self.env.flush_all()
        orderpoint.invalidate_recordset()

        self.assertTrue(orderpoint.exists())
        self.assertFalse(
            orderpoint.qty_to_order_manual_set,
            "Ordering is not the user typing a quantity of their own.",
        )
        orderpoint.product_min_qty = 50
        orderpoint.product_max_qty = 50
        self.env.flush_all()
        orderpoint.invalidate_recordset()
        self.assertEqual(
            orderpoint.qty_to_order,
            40.0,
            "The next shortage must be suggested again.",
        )

    def test_a_muted_orderpoint_would_never_be_procured(self):
        product = self._product("Audit Mute Auto")
        orderpoint = self._orderpoint(product, route_id=self.supply_route.id)
        self.env.flush_all()
        orderpoint.action_replenish()
        self.env.flush_all()
        orderpoint.invalidate_recordset()

        orderpoint.product_min_qty = 100
        orderpoint.product_max_qty = 100
        orderpoint.trigger = "auto"
        self.env.flush_all()
        orderpoint.invalidate_recordset()
        self.assertGreater(orderpoint.qty_to_order_computed, 0.0)
        self.assertEqual(
            orderpoint.qty_to_order,
            orderpoint.qty_to_order_computed,
            "Nothing suppressed the suggestion, so the scheduler will see it.",
        )

    def test_an_explicit_zero_keeps_its_undo(self):
        product = self._product("Audit Undo", suppliable=False)
        orderpoint = self._orderpoint(product, product_min_qty=5, product_max_qty=10)
        self.env.flush_all()
        self.assertEqual(orderpoint.qty_to_order, 10.0)

        orderpoint.qty_to_order = 0
        self.env.flush_all()
        orderpoint.invalidate_recordset()
        self.assertEqual(orderpoint.qty_to_order, 0.0, "the explicit zero sticks")
        self.assertTrue(
            orderpoint.qty_to_order_manual_set,
            "and the undo button, which keys on this, is visible",
        )

        orderpoint.action_remove_manual_qty_to_order()
        self.env.flush_all()
        orderpoint.invalidate_recordset()
        self.assertEqual(orderpoint.qty_to_order, 10.0)
        self.assertFalse(orderpoint.qty_to_order_manual_set)

    def test_searching_qty_to_order_agrees_with_reading_it(self):
        import itertools

        orderpoints = self.Orderpoint
        for index, (manual, manual_set, computed) in enumerate(
            itertools.product([0.0, 5.0], [False, True], [0.0, 7.0]),
        ):
            product = self._product(f"Audit Search {index}", suppliable=False)
            orderpoint = self._orderpoint(
                product,
                product_min_qty=0,
                product_max_qty=0,
            )
            orderpoints |= orderpoint
            self.env.flush_all()
            self.env.cr.execute(
                """
                UPDATE stock_warehouse_orderpoint
                   SET qty_to_order_manual = %s,
                       qty_to_order_manual_set = %s,
                       qty_to_order_computed = %s
                 WHERE id = %s
                """,
                (manual, manual_set, computed, orderpoint.id),
            )
        self.env.invalidate_all()

        comparisons = {
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
            "=": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            "in": lambda a, b: a in b,
            "not in": lambda a, b: a not in b,
        }
        for operator, compare in comparisons.items():
            values = (
                [[0.0], [0.0, 7.0], [5.0]]
                if operator in ("in", "not in")
                else [0.0, 5.0, 7.0]
            )
            for value in values:
                expected = {
                    orderpoint.id
                    for orderpoint in orderpoints
                    if compare(orderpoint.qty_to_order, value)
                }
                found = set(
                    self.Orderpoint.search(
                        [
                            ("id", "in", orderpoints.ids),
                            ("qty_to_order", operator, value),
                        ],
                    ).ids,
                )
                self.assertEqual(
                    found,
                    expected,
                    f"search disagrees with read for qty_to_order {operator} {value}",
                )

    def test_the_report_horizon_never_reaches_a_stored_column(self):
        self.env.company.stock_config_id.horizon_days = 365
        product = self._product("Audit Horizon", suppliable=False)
        self._outgoing(product, 500, days_out=500)
        orderpoint = self._orderpoint(
            product,
            product_min_qty=0,
            product_max_qty=0,
        )
        self.env.flush_all()

        self.env.cr.execute(
            "SELECT qty_to_order_computed, deadline_date "
            "FROM stock_warehouse_orderpoint WHERE id = %s",
            (orderpoint.id,),
        )
        before = self.env.cr.fetchone()

        self.Orderpoint.with_context(
            global_horizon_days=900,
            force_orderpoint_recompute=True,
        ).action_view_orderpoints()
        self.env.flush_all()

        self.env.cr.execute(
            "SELECT qty_to_order_computed, deadline_date "
            "FROM stock_warehouse_orderpoint WHERE id = %s",
            (orderpoint.id,),
        )
        self.assertEqual(
            self.env.cr.fetchone(),
            before,
            "A read-only what-if must not write to the table.",
        )

    def test_the_report_horizon_still_changes_what_the_report_shows(self):
        self.env.company.stock_config_id.horizon_days = 365
        product = self._product("Audit Horizon View", suppliable=False)
        self._outgoing(product, 500, days_out=500)
        orderpoint = self._orderpoint(
            product,
            product_min_qty=0,
            product_max_qty=0,
        )
        self.env.flush_all()
        self.assertEqual(orderpoint.qty_to_order, 0.0)
        self.assertEqual(
            orderpoint.with_context(global_horizon_days=900).qty_to_order,
            500.0,
        )
        self.assertEqual(
            orderpoint.qty_to_order,
            0.0,
            "and the two answers do not contaminate each other's cache",
        )

    def test_lead_days_are_keyed_on_the_horizon_they_were_computed_under(self):
        product = self._product("Audit Horizon Cache", suppliable=False)
        orderpoint = self._orderpoint(product)
        self.env.flush_all()
        near = orderpoint.with_context(global_horizon_days=1).lead_horizon_date
        far = orderpoint.with_context(global_horizon_days=400).lead_horizon_date
        self.assertLess(near, far)

    def test_lead_time_stats_cover_multi_step_receptions(self):
        self.warehouse.reception_steps = "two_steps"
        self.env.flush_all()
        product = self._product("Audit Lead Two Step", suppliable=False)
        orderpoint = self._orderpoint(product)
        picking = self._done_receipt(product, lead_days=6)
        self.assertEqual(picking.location_dest_id, self.warehouse.wh_input_stock_loc_id)

        stats = orderpoint._read_lead_time_stats()
        self.assertEqual(
            stats.get((product.id, self.warehouse.id), (0.0, 0.0, 0)),
            (6.0, 0.0, 1),
        )

    def test_lead_time_stats_do_not_read_around_unflushed_writes(self):
        self.warehouse.reception_steps = "one_step"
        self.env.flush_all()
        product = self._product("Audit Lead Flush", suppliable=False)
        orderpoint = self._orderpoint(product)
        picking = self._done_receipt(product, lead_days=5)
        self.assertEqual(
            orderpoint._read_lead_time_stats()[(product.id, self.warehouse.id)][0],
            5.0,
        )
        picking.date_done += timedelta(days=10)
        self.assertEqual(
            orderpoint._read_lead_time_stats()[(product.id, self.warehouse.id)][0],
            15.0,
            "The query must see what the transaction has already decided.",
        )

    def test_lead_time_stats_of_a_rule_created_after_the_receipt(self):
        self.warehouse.reception_steps = "one_step"
        self.env.flush_all()
        product = self._product("Audit Lead Sequence", suppliable=False)
        picking_type = self._incoming_picking_type()
        picking = self.env["stock.picking"].create(
            {"picking_type_id": picking_type.id},
        )
        self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": product.id,
                "product_uom_qty": 10,
                "location_id": self.suppliers.id,
                "location_dest_id": picking.location_dest_id.id,
            },
        )
        picking.action_confirm()
        picking.move_ids.quantity = 10
        picking.button_validate()
        self.env.cr.execute(
            "UPDATE stock_picking SET create_date = now() - interval '20 days' "
            "WHERE id = %s",
            (picking.id,),
        )
        orderpoint = self._orderpoint(product)
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT lead_time_sample_count FROM stock_warehouse_orderpoint "
            "WHERE id = %s",
            (orderpoint.id,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1)

    def test_supply_warning_follows_the_rules_it_reports_on(self):
        field = self.Orderpoint._fields["show_supply_warning"]
        self.assertTrue(
            self.env.registry.field_depends[field],
            "A compute with no dependencies is cached for the whole transaction.",
        )
        detached = self.env["stock.location"].create(
            {"name": "Audit Detached", "usage": "internal"},
        )
        product = self._product("Audit Warning", suppliable=False)
        orderpoint = self._orderpoint(product, location_id=detached.id)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertFalse(orderpoint.rule_ids, "no rule can reach a detached location")
        self.assertTrue(orderpoint.show_supply_warning)
        route = self.env["stock.route"].create(
            {
                "name": "Audit Detached Supply",
                "product_selectable": True,
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Audit: Vendors -> Detached",
                            "action": "pull",
                            "procure_method": "make_to_stock",
                            "picking_type_id": self._incoming_picking_type().id,
                            "location_src_id": self.suppliers.id,
                            "location_dest_id": detached.id,
                        },
                    ),
                ],
            },
        )
        product.route_ids = [(6, 0, route.ids)]
        self.env.flush_all()
        self.assertTrue(orderpoint.rule_ids)
        self.assertFalse(
            orderpoint.show_supply_warning,
            "The warning must clear as soon as a rule reaches the location.",
        )

    def test_a_procurement_warning_is_not_matched_by_wildcards(self):
        template = self._product("Alcohol 70 PERCENT", suppliable=False).product_tmpl_id
        model_id = self.env.ref("product.model_product_template").id
        self.env["mail.activity"].search([]).unlink()
        template.with_user(1).activity_schedule(
            "mail.mail_activity_data_warning",
            note="No rule has been found to replenish Alcohol 70 PERCENT in WH.",
            user_id=1,
        )
        self.env.flush_all()
        from odoo.tools import escape_psql

        message = "No rule has been found to replenish Alcohol 70% in WH."
        self.assertEqual(
            self.env["mail.activity"].search_count(
                [
                    ("res_model_id", "=", model_id),
                    ("note", "=like", f"%{escape_psql(message)}%"),
                ],
            ),
            0,
            "Another product's warning must not satisfy this one's guard.",
        )

    def test_a_failed_procurement_batch_is_rolled_back(self):
        import inspect

        from odoo.addons.stock.models.stock_orderpoint_replenish import (
            StockWarehouseOrderpointReplenish,
        )

        source = inspect.getsource(
            StockWarehouseOrderpointReplenish._procure_orderpoint_confirm,
        )
        self.assertIn("cr.rollback()", source)
        self.assertIn("committed = True", source)
        commit_index = source.index("cr.commit()")
        finally_index = source.index("finally:")
        self.assertLess(
            commit_index,
            finally_index,
            "The commit belongs on the success path, not in the cleanup.",
        )

    def test_replenishment_list_does_not_scale_with_the_number_of_rows(self):
        products = self.env["product.product"].create(
            [
                {
                    "name": f"Audit Scale {index}",
                    "is_storable": True,
                    "route_ids": [(6, 0, self.supply_route.ids)],
                    "seller_ids": [
                        (
                            0,
                            0,
                            {
                                "partner_id": self.vendor.id,
                                "min_qty": 0,
                                "price": 1,
                                "delay": 3,
                            },
                        ),
                    ],
                }
                for index in range(12)
            ],
        )
        orderpoints = self.Orderpoint.create(
            [
                {
                    "product_id": product.id,
                    "location_id": self.stock_location.id,
                    "warehouse_id": self.warehouse.id,
                    "product_min_qty": 10,
                    "product_max_qty": 20,
                    "trigger": "manual",
                    "route_id": self.supply_route.id,
                }
                for product in products
            ],
        )
        self.env.flush_all()
        columns = [
            "product_id",
            "location_id",
            "qty_on_hand",
            "qty_forecast",
            "qty_to_order",
            "unwanted_replenish",
            "route_id_placeholder",
            "replenishment_uom_id_placeholder",
            "show_supply_warning",
            "deadline_date",
            "effective_route_id",
            "trigger",
        ]

        queries = []
        cursor_class = type(self.env.cr)
        original_execute = cursor_class.execute

        def counting(cursor, query, params=None, *args, **kwargs):
            queries.append(1)
            return original_execute(cursor, query, params, *args, **kwargs)

        def count(records):
            self.env.invalidate_all()
            queries.clear()
            self.patch(cursor_class, "execute", counting)
            try:
                records.read(columns)
            finally:
                cursor_class.execute = original_execute
            return len(queries)

        few = count(orderpoints[:3])
        many = count(orderpoints)
        _logger.info("replenishment read: 3 rows %d q, 12 rows %d q", few, many)
        self.assertLessEqual(
            many - few,
            few,
            f"Reading 12 rows cost {many} queries against {few} for 3: the report "
            f"is scaling with the number of rows again.",
        )

    def _incoming(self, product, quantity, days_out):
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": quantity,
                "location_id": self.suppliers.id,
                "location_dest_id": self.stock_location.id,
                "date": fields.Datetime.now() + timedelta(days=days_out),
            },
        )
        move._action_confirm()
        return move

    def test_the_report_horizon_never_reaches_a_procurement_date(self):
        product = self._product("Audit Horizon Procurement")
        orderpoint = self._orderpoint(
            product,
            product_max_qty=20,
            trigger="auto",
            route_id=self.supply_route.id,
        )
        self.env.company.stock_config_id.horizon_days = 5
        self.env.flush_all()
        self.env.invalidate_all()
        planned = orderpoint._prepare_procurements({})[0].values["date_planned"]
        for horizon in (30, 60, 365):
            self.env.invalidate_all()
            widened = orderpoint.with_context(global_horizon_days=horizon)
            self.assertEqual(
                widened._prepare_procurements({})[0].values["date_planned"],
                planned,
                "The search panel's horizon is a what-if control over what the "
                "report shows. lead_horizon_date follows it, so the subtraction "
                "that removes the horizon again has to follow it too -- otherwise "
                "widening the view pushes the real order out by the difference.",
            )

    def test_the_scheduler_refreshes_manual_orderpoints_too(self):
        orderpoints = {}
        for trigger in ("auto", "manual"):
            product = self._product(f"Audit Scheduler {trigger}", suppliable=False)
            orderpoints[trigger] = self._orderpoint(
                product,
                product_max_qty=20,
                trigger=trigger,
            )
        self.env.flush_all()
        for orderpoint in orderpoints.values():
            self.assertEqual(orderpoint.qty_to_order_computed, 20.0)
            self.env["stock.quant"]._update_available_quantity(
                orderpoint.product_id,
                self.stock_location,
                100.0,
            )
        self.env.flush_all()
        self.env.invalidate_all()
        self.env["stock.scheduler"]._run_tasks()
        self.env.flush_all()
        self.env.invalidate_all()
        for trigger, orderpoint in orderpoints.items():
            self.assertEqual(
                orderpoint.qty_to_order_computed,
                0.0,
                f"A {trigger} orderpoint's stored suggestion went stale. The "
                "scheduler must not carry the procurement half's trigger filter "
                "over to the recompute: the replenishment report is manual rows, "
                "its To Reorder filter searches this column, and the autovacuum "
                "deletes on it.",
            )

    def test_the_vacuum_runs_on_a_refreshed_suggestion(self):
        product = self._product("Audit Vacuum", suppliable=False)
        orderpoint = self._orderpoint(
            product,
            product_max_qty=20,
            trigger="manual",
            is_autogenerated=True,
        )
        self.env.flush_all()
        self.assertEqual(orderpoint.qty_to_order_computed, 20.0)
        self.env["stock.quant"]._update_available_quantity(
            product,
            self.stock_location,
            100.0,
        )
        self.env.flush_all()
        self.env.invalidate_all()
        self.Orderpoint.with_context(
            force_orderpoint_recompute=True,
        ).action_view_orderpoints()
        self.assertFalse(
            orderpoint.exists(),
            "Nothing is left to order, so the autogenerated row is spent. It "
            "survived while the vacuum ran before the refresh that corrects the "
            "column the vacuum selects on.",
        )

    def test_a_late_arrival_does_not_hide_an_earlier_shortage(self):
        self.stock_location.replenish_location = True
        self.env.company.stock_config_id.horizon_days = 30
        cases = {
            "no arrival at all": None,
            "arrival past the horizon": 90,
            "arrival inside the horizon": 10,
        }
        detected = {}
        for label, arrival in cases.items():
            product = self._product(f"Audit Shortage {label}", suppliable=False)
            self._outgoing(product, 100, 3)
            if arrival is not None:
                self._incoming(product, 200, arrival)
            self.env.flush_all()
            self.env.invalidate_all()
            shortages = self.env[
                "stock.replenishment.report"
            ]._get_projected_shortages()
            detected[label] = shortages.get(
                (product.id, self.stock_location.id),
            )
        self.assertEqual(
            detected["no arrival at all"],
            -100.0,
            "control: an uncovered shortage inside the horizon must be reported.",
        )
        self.assertEqual(
            detected["arrival past the horizon"],
            -100.0,
            "The cheap pass that decides who gets a horizon forecast may over-"
            "select and may never under-select: a delivery scheduled after the "
            "horizon cannot cancel a stockout that happens before it.",
        )
        self.assertIsNone(
            detected["arrival inside the horizon"],
            "negative control: an arrival the horizon actually covers is not a "
            "shortage, and the exact pass is what has to say so.",
        )

    def _receipt(self, product, quantity, ordered_days_ago, done_days_ago=0):
        picking_type = self._incoming_picking_type()
        picking = self.env["stock.picking"].create({"picking_type_id": picking_type.id})
        self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": product.id,
                "product_uom_qty": quantity,
                "location_id": self.suppliers.id,
                "location_dest_id": picking.location_dest_id.id,
            },
        )
        picking.action_confirm()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE stock_picking SET create_date = now() - %s::interval WHERE id = %s",
            (f"{ordered_days_ago} days", picking.id),
        )
        self.env.invalidate_all()
        return picking

    def _validate(self, picking, quantity, done_days_ago):
        picking.move_ids.move_line_ids.quantity = quantity
        picking.move_ids.picked = True
        result = picking.button_validate()
        if isinstance(result, dict) and result.get("res_model") == (
            "stock.backorder.confirmation"
        ):
            self.env["stock.backorder.confirmation"].with_context(
                result["context"],
            ).create({}).process()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE stock_picking SET date_done = now() - %s::interval WHERE id = %s",
            (f"{done_days_ago} days", picking.id),
        )
        self.env.invalidate_all()
        return self.env["stock.picking"].search([("backorder_id", "=", picking.id)])

    def test_lead_time_counts_the_wait_a_backorder_imposes(self):
        product = self._product("Audit Backorder Lead", suppliable=False)
        orderpoint = self._orderpoint(product)
        ordered_days_ago = 40
        picking = self._receipt(product, 100, ordered_days_ago)
        backorder = self._validate(picking, 10, done_days_ago=38)
        self.assertTrue(backorder, "a partial receipt must leave a backorder")
        self._validate(backorder, 90, done_days_ago=0)

        orderpoint._compute_lead_time_stats()
        self.assertEqual(
            orderpoint.lead_time_sample_count,
            2,
            "Excluding rows with a backorder_id dropped the second delivery "
            "entirely, so only the early sliver of the order was measured.",
        )
        self.assertAlmostEqual(
            orderpoint.actual_lead_time_avg,
            (2 + ordered_days_ago) / 2,
            places=0,
            msg="Each receipt is measured from the order that started the chain, "
            "not from the moment its own backorder was split off.",
        )
        self.assertGreater(
            orderpoint.actual_lead_time_stddev,
            0.0,
            "A supplier who delivered 10%% on time and the rest five weeks late "
            "was being recorded with zero variance -- the single worst answer "
            "for the safety-stock maths downstream.",
        )

    def test_a_manual_orderpoint_is_told_what_its_order_created(self):
        source = self.env["stock.warehouse"].create(
            {"name": "Audit Source", "code": "ASRC"},
        )
        self.warehouse.resupply_wh_ids = [(6, 0, source.ids)]
        self.env.flush_all()
        resupply_route = self.warehouse.resupply_route_ids
        self.assertTrue(resupply_route, "the resupply route must have been created")
        notifications = {}
        for trigger in ("auto", "manual"):
            product = self._product(f"Audit Notify {trigger}", suppliable=False)
            product.route_ids = [(6, 0, resupply_route.ids)]
            orderpoint = self._orderpoint(
                product,
                product_max_qty=20,
                trigger=trigger,
                route_id=resupply_route.id,
            )
            self.env.flush_all()
            notifications[trigger] = orderpoint.action_replenish()
        self.assertTrue(
            notifications["auto"],
            "control: an auto orderpoint has always been told.",
        )
        self.assertTrue(
            notifications["manual"],
            "_prepare_procurement_vals records orderpoint_id only for auto rows, "
            "so a source domain keyed on it could never find a manual row's own "
            "order -- and the report generates every one of its rows as manual, "
            "which makes its Order button exactly the case that stayed silent.",
        )

    def test_the_action_context_carries_only_what_the_report_needs(self):
        action = self.Orderpoint.with_context(
            active_model="product.template",
            active_id=42,
            force_orderpoint_recompute=True,
            search_default_filter_to_reorder=True,
        ).action_view_orderpoints()
        context = action["context"]
        self.assertIn("search_default_filter_to_reorder", context)
        for leaked in ("active_model", "active_id", "force_orderpoint_recompute"):
            self.assertNotIn(
                leaked,
                context,
                f"{leaked} rode the caller's context back out to the client. "
                "product_id's domain branches on active_model, so a leaked one "
                "silently narrows the product dropdown on the report.",
            )

    def test_one_unreplenishable_orderpoint_does_not_silence_the_whole_batch(self):
        good = self._product("Audit Batch Good")
        bad = self._product("Audit Batch Bad", suppliable=False)
        orderpoints = self._orderpoint(good, trigger="auto") + self._orderpoint(
            bad,
            trigger="auto",
            location_id=self._unsuppliable_location("Audit Batch Nowhere").id,
        )
        self.env.flush_all()

        failures = orderpoints._run_procurement_batch({}, raise_user_error=False)

        self.assertEqual(
            [orderpoint.product_id for orderpoint, _msg in failures],
            [bad],
            "only the orderpoint no rule can reach should have failed",
        )
        self.assertEqual(
            self.env["stock.move"].search_count(
                [
                    ("product_id", "=", good.id),
                    ("location_dest_id", "=", self.stock_location.id),
                ]
            ),
            1,
            "the orderpoint that had a rule must still have been procured",
        )
