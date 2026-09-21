from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tests import TransactionCase, tagged

from odoo.addons.stock.models.stock_procurement import ProcurementException


class ProcRuleAuditCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")

    def _product(self, name, routes=None):
        return self.env["product.product"].create(
            {
                "name": name,
                "is_storable": True,
                "type": "consu",
                "route_ids": [Command.set(routes.ids)] if routes is not None else [],
            },
        )

    def _rule(self, name, route, source, destination, **extra):
        return self.env["stock.rule"].create(
            {
                "name": name,
                "route_id": route.id,
                "action": "pull",
                "location_src_id": source.id,
                "location_dest_id": destination.id,
                "procure_method": "make_to_stock",
                "picking_type_id": self.warehouse.int_type_id.id,
                **extra,
            },
        )


class TestRuleFormConsistency(ProcRuleAuditCommon):
    def test_a_global_route_keeps_the_operation_type_it_was_given(self):
        global_route = self.env["stock.route"].create(
            {"name": "Company-less route", "company_id": False},
        )
        rule = self.env["stock.rule"].new(
            {
                "name": "Form rule",
                "action": "pull",
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_dest_id": self.stock_location.id,
                "company_id": self.env.company.id,
            },
        )
        rule.route_id = global_route
        rule._onchange_route()
        self.assertEqual(
            rule.picking_type_id,
            self.warehouse.out_type_id,
            "a route that names no company constrains no operation type",
        )

    def test_a_route_of_another_company_still_clears_the_operation_type(self):
        other_company = self.env["res.company"].create({"name": "Rule Audit Co"})
        other_route = self.env["stock.route"].create(
            {"name": "Other company route", "company_id": other_company.id},
        )
        rule = self.env["stock.rule"].new(
            {
                "name": "Form rule",
                "action": "pull",
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_dest_id": self.stock_location.id,
                "company_id": self.env.company.id,
            },
        )
        rule.route_id = other_route
        rule._onchange_route()
        self.assertFalse(rule.picking_type_id)

    def test_push_applicability_is_rejected_when_it_is_not_a_domain(self):
        route = self.env["stock.route"].create({"name": "Push audit route"})
        rule = self._rule(
            "Push rule",
            route,
            self.stock_location,
            self.customer_location,
            action="push",
        )
        with self.assertRaises(ValidationError):
            rule.push_domain = "this is not a domain"
        with self.assertRaises(ValidationError):
            rule.push_domain = "[('no_such_field', '=', 1)]"
        rule.push_domain = "[('product_uom_qty', '>', 0)]"
        self.assertEqual(rule.push_domain, "[('product_uom_qty', '>', 0)]")

    def test_the_operation_type_code_domain_composes_across_modules(self):
        rule = self.env["stock.rule"].search([("action", "=", "pull")], limit=1)
        self.assertEqual(rule._get_domain_picking_type_code(), [])


class TestProcurementMoveValues(ProcRuleAuditCommon):
    def test_the_rule_address_survives_a_procurement_that_names_no_partner(self):
        address = self.env["res.partner"].create({"name": "Rule address"})
        route = self.env["stock.route"].create({"name": "Address route"})
        rule = self._rule(
            "Address rule",
            route,
            self.supplier_location,
            self.stock_location,
            partner_address_id=address.id,
        )
        product = self._product("Address product")
        values = {
            "date_planned": "2026-09-01 00:00:00",
            "company_id": self.env.company,
            "partner_id": False,
        }
        move_values = rule._prepare_stock_move_vals(
            self.env["stock.rule"].Procurement(
                product,
                1.0,
                product.uom_id,
                self.stock_location,
                product.display_name,
                "audit",
                self.env.company,
                values,
            ),
        )
        self.assertEqual(move_values["partner_id"], address.id)

    def test_a_procurement_partner_is_still_used_when_the_rule_names_none(self):
        partner = self.env["res.partner"].create({"name": "Procurement partner"})
        route = self.env["stock.route"].create({"name": "No address route"})
        rule = self._rule(
            "No address rule",
            route,
            self.supplier_location,
            self.stock_location,
        )
        product = self._product("No address product")
        move_values = rule._prepare_stock_move_vals(
            self.env["stock.rule"].Procurement(
                product,
                1.0,
                product.uom_id,
                self.stock_location,
                product.display_name,
                "audit",
                self.env.company,
                {
                    "date_planned": "2026-09-01 00:00:00",
                    "company_id": self.env.company,
                    "partner_id": partner.id,
                },
            ),
        )
        self.assertEqual(move_values["partner_id"], partner.id)

    def test_every_misconfigured_rule_in_a_batch_is_reported(self):
        route = self.env["stock.route"].create({"name": "Sourceless route"})
        rules = [
            self.env["stock.rule"].create(
                {
                    "name": f"No source {index}",
                    "route_id": route.id,
                    "action": "pull",
                    "location_dest_id": self.customer_location.id,
                    "procure_method": "make_to_stock",
                    "picking_type_id": self.warehouse.out_type_id.id,
                },
            )
            for index in range(3)
        ]
        Procurement = self.env["stock.rule"].Procurement
        pairs = [
            (
                Procurement(
                    self._product(f"Sourceless {index}"),
                    1.0,
                    self.env.ref("uom.product_uom_unit"),
                    self.customer_location,
                    "audit",
                    "audit",
                    self.env.company,
                    {
                        "company_id": self.env.company,
                        "date_planned": "2026-09-01 00:00:00",
                    },
                ),
                rule,
            )
            for index, rule in enumerate(rules)
        ]
        with self.assertRaises(ProcurementException) as caught:
            self.env["stock.rule"]._run_pull(pairs)
        self.assertEqual(len(caught.exception.procurement_exceptions), 3)


class TestRuleResolution(ProcRuleAuditCommon):
    def _competing_rules(self):
        route = self.env["stock.route"].create(
            {"name": "Precedence route", "product_selectable": True, "sequence": 1},
        )
        destination = self.env["stock.location"].create(
            {
                "name": "Precedence dest",
                "location_id": self.warehouse.view_location_id.id,
            },
        )
        unscoped = self._rule(
            "Unscoped seq 10",
            route,
            self.stock_location,
            destination,
            sequence=10,
            warehouse_id=False,
        )
        scoped = self._rule(
            "Warehouse seq 50",
            route,
            self.stock_location,
            destination,
            sequence=50,
            warehouse_id=self.warehouse.id,
        )
        product = self._product("Precedence product", routes=route)
        return product, destination, unscoped, scoped

    def test_both_resolvers_prefer_the_same_rule(self):
        product, destination, _unscoped, scoped = self._competing_rules()
        pull_choice = (
            self.env["stock.rule"]
            .sudo()
            ._get_rule(
                product,
                destination,
                {"warehouse_id": self.warehouse, "company_id": self.env.company},
            )
        )
        push_choice = (
            self.env["stock.rule"]
            .sudo()
            ._get_domain_rule_by(
                self.env["stock.route"],
                False,
                product,
                self.warehouse,
                [("location_dest_id", "=", destination.id), ("action", "!=", "push")],
            )
        )
        self.assertEqual(pull_choice, scoped)
        self.assertEqual(push_choice, scoped, "both resolvers, one precedence")

    def test_a_move_and_the_procurement_that_feeds_it_agree(self):
        product, destination, _unscoped, scoped = self._competing_rules()
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 1,
                "location_id": self.stock_location.id,
                "location_dest_id": destination.id,
                "picking_type_id": self.warehouse.int_type_id.id,
            },
        )
        move._update_procure_method()
        procurement_choice = (
            self.env["stock.rule"]
            .sudo()
            ._get_rule(
                product,
                destination,
                {"warehouse_id": self.warehouse, "company_id": self.env.company},
            )
        )
        self.assertEqual(move.rule_id, scoped)
        self.assertEqual(move.rule_id, procurement_choice)

    def test_a_batch_resolves_each_procurement_against_its_own_scope(self):
        marker_route = self.env["stock.route"].create(
            {"name": "Marker route", "product_selectable": True, "sequence": 1},
        )
        marker_rule = self._rule(
            "Marker rule",
            marker_route,
            self.stock_location,
            self.customer_location,
            sequence=1,
        )
        product = self._product("Batch scope product", routes=marker_route)
        Procurement = self.env["stock.rule"].Procurement
        base = {
            "company_id": self.env.company,
            "warehouse_id": self.warehouse,
            "date_planned": "2026-09-01 00:00:00",
        }

        def procurement(name, **extra):
            return Procurement(
                product,
                1.0,
                product.uom_id,
                self.customer_location,
                name,
                name,
                self.env.company,
                dict(base, **extra),
            )

        plain = procurement("plain")
        narrowed = procurement("narrowed", audit_scope_marker=True)

        Rule = self.env["stock.rule"]

        original_scope = type(Rule)._get_domain_rule_scope

        def scoped_domain(rule_self, values):
            domain = original_scope(rule_self, values)
            if values.get("audit_scope_marker"):
                domain &= Domain("id", "!=", marker_rule.id)
            return domain

        type(Rule)._get_domain_rule_scope = scoped_domain
        try:
            alone = [
                Rule.sudo()._get_rules_batch([plain])[0],
                Rule.sudo()._get_rules_batch([narrowed])[0],
            ]
            forward = Rule.sudo()._get_rules_batch([plain, narrowed])
            backward = Rule.sudo()._get_rules_batch([narrowed, plain])
        finally:
            type(Rule)._get_domain_rule_scope = original_scope

        self.assertEqual(list(forward), alone, "batching must not change the answer")
        self.assertEqual(list(reversed(backward)), alone, "nor must batch order")
        self.assertNotEqual(
            alone[0],
            alone[1],
            "the marker override must actually change one of the two",
        )


class TestProcurementContract(ProcRuleAuditCommon):
    def _procurement(self, **values):
        product = self._product("Contract product")
        return self.env["stock.rule"].Procurement(
            product,
            1.0,
            product.uom_id,
            self.customer_location,
            "audit",
            "audit",
            self.env.company,
            values,
        )

    def test_run_does_not_rewrite_the_caller_values(self):
        values = {}
        procurement = self._procurement(**values)
        procurement.values.update(values)
        with self.assertRaises(UserError):
            self.env["stock.rule"].run([procurement])
        self.assertEqual(
            procurement.values,
            {},
            "run must fill its defaults on a copy",
        )

    def test_a_skipped_procurement_is_not_touched_either(self):
        service = self.env["product.product"].create(
            {"name": "Audit service", "type": "service"},
        )
        procurement = self.env["stock.rule"].Procurement(
            service,
            1.0,
            service.uom_id,
            self.customer_location,
            "audit",
            "audit",
            self.env.company,
            {},
        )
        self.env["stock.rule"].run([procurement])
        self.assertEqual(procurement.values, {})

    def test_an_action_no_module_implements_is_named_in_the_error(self):
        runners = self.env["stock.rule"]._get_action_runners()
        self.assertEqual(runners["pull"], "_run_pull")
        self.assertNotIn(
            "push",
            runners,
            "a procurement never carries `push`: the rule domain excludes it "
            "and `pull_push` is dispatched as `pull`",
        )


class TestTransitPartner(ProcRuleAuditCommon):
    def test_the_transit_partner_is_stamped_on_every_waiting_move_at_once(self):
        transit = self.env.company.stock_config_id.internal_transit_location_id
        route = self.env["stock.route"].create({"name": "Transit route"})
        rule = self._rule("Transit rule", route, self.stock_location, transit)
        supplier_partner = self.warehouse.partner_id or self.env.company.partner_id
        procurements = []
        waiting_moves = self.env["stock.move"]
        for index in range(4):
            product = self._product(f"Transit product {index}")
            guess = self.env["res.partner"].create({"name": f"Guess {index}"})
            waiting = self.env["stock.move"].create(
                {
                    "product_id": product.id,
                    "product_uom_qty": 1,
                    "location_id": transit.id,
                    "location_dest_id": self.stock_location.id,
                    "picking_type_id": self.warehouse.in_type_id.id,
                    "partner_id": guess.id,
                },
            )
            waiting_moves |= waiting
            procurements.append(
                (
                    self.env["stock.rule"].Procurement(
                        product,
                        1.0,
                        product.uom_id,
                        transit,
                        "audit",
                        "audit",
                        self.env.company,
                        {"company_id": self.env.company, "move_dest_ids": waiting},
                    ),
                    rule,
                ),
            )
        self.env.flush_all()
        self.env["stock.rule"]._propagate_transit_partner(procurements)
        self.env.flush_all()
        self.assertEqual(
            waiting_moves.partner_id,
            supplier_partner,
            "all four moves take the supplying warehouse's partner",
        )


@tagged("post_install", "-at_install")
class TestPushBatchCost(ProcRuleAuditCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse.reception_steps = "two_steps"
        cls.env.flush_all()

    def _push_cost(self, count):
        products = self.env["product.product"].create(
            [
                {
                    "name": f"Push cost {count}-{index}",
                    "is_storable": True,
                    "type": "consu",
                }
                for index in range(count)
            ],
        )
        moves = self.env["stock.move"].create(
            [
                {
                    "product_id": product.id,
                    "product_uom_qty": 1,
                    "location_id": self.supplier_location.id,
                    "location_dest_id": self.warehouse.wh_input_stock_loc_id.id,
                    "picking_type_id": self.warehouse.in_type_id.id,
                }
                for product in products
            ],
        )
        moves._action_confirm()
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.cr.sql_statement_count
        moves._push_apply()
        self.env.flush_all()
        return self.cr.sql_statement_count - before, moves

    def test_pushing_a_batch_costs_no_create_per_move(self):
        few_queries, _few = self._push_cost(2)
        many_queries, many_moves = self._push_cost(40)
        marginal = many_queries - few_queries
        self.assertLessEqual(
            marginal,
            80,
            f"38 further pushed moves cost {marginal} extra queries "
            f"(2 moves: {few_queries}, 40 moves: {many_queries})",
        )
        pushed = self.env["stock.move"].search(
            [("move_orig_ids", "in", many_moves.ids)]
        )
        self.assertEqual(len(pushed), 40, "every move still gets its own push")
        self.assertEqual(
            pushed.location_id,
            self.warehouse.wh_input_stock_loc_id,
            "and it still starts where the move it follows ended",
        )
