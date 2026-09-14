from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductTemplateStockInvariants(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Tmpl = cls.env["product.template"]

    def _assert_refused(self, callback):
        with self.assertRaises(ValidationError) as caught:
            callback()
        self.assertRegex(
            str(caught.exception),
            "cannot track inventory|cannot be\n? *tracked by lot",
        )

    def test_a_service_cannot_be_created_tracking_inventory(self):
        self._assert_refused(
            lambda: self.Tmpl.create(
                {"name": "svc", "type": "service", "is_storable": True},
            ),
        )

    def test_a_combo_cannot_be_created_tracking_inventory(self):
        choice = self.env["product.combo"].create(
            {
                "name": "audit choice",
                "combo_item_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.Tmpl.create(
                                {"name": "combo member", "type": "consu"},
                            ).product_variant_id.id,
                        },
                    ),
                ],
            },
        )
        self._assert_refused(
            lambda: self.Tmpl.create(
                {
                    "name": "combo",
                    "type": "combo",
                    "is_storable": True,
                    "combo_ids": [(6, 0, choice.ids)],
                },
            ),
        )

    def test_the_variant_model_is_guarded_too(self):
        self._assert_refused(
            lambda: self.env["product.product"].create(
                {"name": "svc variant", "type": "service", "is_storable": True},
            ),
        )
        service = self.Tmpl.create({"name": "svc3", "type": "service"})
        self._assert_refused(
            lambda: service.product_variant_id.write({"is_storable": True}),
        )

    def test_writing_both_at_once_no_longer_bypasses_the_compute(self):
        template = self.Tmpl.create(
            {"name": "goods", "type": "consu", "is_storable": True},
        )
        self._assert_refused(
            lambda: template.write({"type": "service", "is_storable": True}),
        )

    def test_the_action_context_default_does_not_break_the_form(self):
        form = Form(self.Tmpl.with_context(default_is_storable=True))
        form.name = "from a default_is_storable action"
        self.assertTrue(form.is_storable)
        form.type = "service"
        self.assertFalse(form.is_storable)
        record = form.save()
        self.assertEqual((record.type, record.is_storable), ("service", False))

    def test_changing_the_type_alone_still_normalises_silently(self):
        template = self.Tmpl.create(
            {"name": "goods2", "type": "consu", "is_storable": True, "tracking": "lot"},
        )
        template.write({"type": "service"})
        self.assertFalse(template.is_storable)
        self.assertEqual(template.tracking, "none")

    def test_the_client_save_path_still_works(self):
        template = self.Tmpl.create(
            {"name": "web", "type": "consu", "is_storable": True, "tracking": "lot"},
        )
        onchange = template.onchange(
            {
                "id": template.id,
                "type": "service",
                "is_storable": True,
                "tracking": "lot",
            },
            ["type"],
            {"type": {}, "is_storable": {}, "tracking": {}},
        )
        self.assertEqual(
            onchange["value"],
            {"is_storable": False, "tracking": "none"},
        )
        template.web_save({"type": "service"}, {"is_storable": {}, "tracking": {}})
        self.assertEqual((template.type, template.is_storable), ("service", False))

    def test_a_non_storable_product_cannot_be_lot_tracked(self):
        self._assert_refused(
            lambda: self.Tmpl.create(
                {
                    "name": "untracked",
                    "type": "consu",
                    "is_storable": False,
                    "tracking": "lot",
                },
            ),
        )

    def test_tracking_defaulted_onto_a_non_storable_product_is_refused(self):
        self._assert_refused(
            lambda: self.Tmpl.create({"name": "implicit", "tracking": "lot"}),
        )

    def test_assignment_order_matters_and_is_documented(self):
        template = self.Tmpl.create({"name": "order", "type": "consu"})
        self._assert_refused(lambda: setattr(template, "tracking", "serial"))

        template.is_storable = True
        template.tracking = "serial"
        self.assertEqual(template.tracking, "serial")

        other = self.Tmpl.create({"name": "order2", "type": "consu"})
        other.write({"is_storable": True, "tracking": "serial"})
        self.assertEqual(other.tracking, "serial")

    def test_a_variant_write_naming_both_is_order_independent(self):
        for index, vals in enumerate(
            (
                {"is_storable": True, "tracking": "serial"},
                {"tracking": "serial", "is_storable": True},
            ),
        ):
            variant = self.env["product.product"].create(
                {"name": f"split {index}", "type": "consu"},
            )
            variant.write(vals)
            self.assertEqual(
                (variant.is_storable, variant.tracking),
                (True, "serial"),
                f"a variant write is not atomic for {list(vals)}",
            )

    def test_a_variant_write_still_refuses_a_real_contradiction(self):
        variant = self.env["product.product"].create(
            {"name": "split bad", "type": "consu"},
        )
        self._assert_refused(
            lambda: variant.write({"type": "service", "is_storable": True}),
        )

    def test_clearing_storability_still_clears_tracking_silently(self):
        template = self.Tmpl.create(
            {"name": "drop", "type": "consu", "is_storable": True, "tracking": "lot"},
        )
        template.write({"is_storable": False})
        self.assertEqual(template.tracking, "none")

    def test_a_storable_product_is_still_free_to_be_lot_tracked(self):
        template = self.Tmpl.create(
            {"name": "ok", "type": "consu", "is_storable": True, "tracking": "lot"},
        )
        self.assertEqual(template.tracking, "lot")


@tagged("post_install", "-at_install")
class TestSerialPrefixSequences(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Tmpl = cls.env["product.template"]

    def test_returning_to_a_prefix_resumes_its_numbering(self):
        template = self.Tmpl.create(
            {
                "name": "prefix reuse",
                "type": "consu",
                "is_storable": True,
                "tracking": "serial",
            },
        )
        template.serial_prefix_format = "ZZZ-"
        self.env.flush_all()
        first = template.lot_sequence_id
        drawn = [first.next_by_id() for _ in range(3)]
        self.assertEqual(drawn, ["ZZZ-0000001", "ZZZ-0000002", "ZZZ-0000003"])

        template.serial_prefix_format = "YYY-"
        self.env.flush_all()
        self.assertNotEqual(template.lot_sequence_id, first)
        self.assertTrue(
            first.exists(),
            "the sequence for ZZZ- still owns the numbering for ZZZ-",
        )

        template.serial_prefix_format = "ZZZ-"
        self.env.flush_all()
        self.assertEqual(template.lot_sequence_id, first)
        self.assertEqual(
            template.lot_sequence_id.preview_next(),
            "ZZZ-0000004",
            "returning to a prefix must not reissue names already drawn",
        )

    def test_clearing_the_prefix_returns_to_the_standard_sequence(self):
        template = self.Tmpl.create(
            {
                "name": "prefix clear",
                "type": "consu",
                "is_storable": True,
                "tracking": "serial",
            },
        )
        template.serial_prefix_format = "QQQ-"
        self.env.flush_all()
        template.serial_prefix_format = ""
        self.env.flush_all()
        self.assertEqual(
            template.lot_sequence_id,
            self.Tmpl._default_lot_sequence_id(),
        )


@tagged("post_install", "-at_install")
class TestProductTemplateStorabilityOff(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Tmpl = cls.env["product.template"]
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.customers = cls.env.ref("stock.stock_location_customers")

    def _stocked_product(self, name, quantity=10.0):
        template = self.Tmpl.create(
            {"name": name, "type": "consu", "is_storable": True},
        )
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": template.product_variant_id.id,
                "location_id": self.stock_location.id,
                "inventory_quantity": quantity,
            },
        )._apply_inventory()
        return template

    def _reserved_delivery(self, product, quantity=4.0):
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": quantity,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customers.id,
                "company_id": self.env.company.id,
            },
        )
        move._action_confirm()
        move._action_assign()
        return move

    def _get_quant(self, product):
        return self.env["stock.quant"].search(
            [
                ("product_id", "=", product.id),
                ("location_id", "=", self.stock_location.id),
            ],
        )

    def test_turning_storability_off_releases_the_reservation(self):
        template = self._stocked_product("strand")
        product = template.product_variant_id
        move = self._reserved_delivery(product)
        self.assertEqual(self._get_quant(product).reserved_quantity, 4.0)

        template.write({"is_storable": False})

        self.assertEqual(
            self._get_quant(product).reserved_quantity,
            0.0,
            "turning inventory tracking off must release what nothing else can",
        )
        move._action_cancel()

    def test_validating_the_move_afterwards_leaves_nothing_reserved(self):
        template = self._stocked_product("strand2")
        product = template.product_variant_id
        move = self._reserved_delivery(product)
        template.write({"is_storable": False})

        move.quantity = 4.0
        move.picked = True
        move._action_done()

        quant = self._get_quant(product)
        self.assertEqual(quant.reserved_quantity, 0.0)
        self.assertEqual(
            product.qty_free,
            quant.quantity,
            "qty_free must not stay short by a reservation nobody owns",
        )

    def test_what_the_release_leaves_behind_is_the_move(self):
        template = self._stocked_product("leftover")
        product = template.product_variant_id
        move = self._reserved_delivery(product)

        template.write({"is_storable": False})
        self.env.invalidate_all()

        self.assertEqual(self._get_quant(product).reserved_quantity, 0.0)
        self.assertEqual(product.qty_free, 10.0)
        self.assertEqual(move.state, "assigned")
        self.assertEqual(sum(move.move_line_ids.mapped("quantity")), 4.0)

        move._unreserve()
        self.assertEqual(move.state, "confirmed")
        self.assertFalse(move.move_line_ids)
        self.assertEqual(self._get_quant(product).reserved_quantity, 0.0)

    def test_turning_storability_on_still_resets_the_inventory(self):
        template = self.Tmpl.create(
            {"name": "flipon", "type": "consu", "is_storable": False},
        )
        product = template.product_variant_id
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 5.0,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.stock_location.id,
                "company_id": self.env.company.id,
            },
        )
        move._action_confirm()
        move.quantity = 5.0
        move.picked = True
        move._action_done()

        template.write({"is_storable": True})

        self.assertEqual(product.qty_available, 0.0)
        self.assertTrue(
            self.env["stock.move"].search_count(
                [
                    ("product_id", "=", product.id),
                    ("location_dest_id.usage", "=", "inventory"),
                    ("state", "=", "done"),
                ],
            ),
            "the ledger/stock disagreement must be booked, not left implicit",
        )


@tagged("post_install", "-at_install")
class TestProductTemplateQuantityMessages(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Tmpl = cls.env["product.template"]

    def test_an_archived_only_template_is_not_told_to_save_itself(self):
        template = self.Tmpl.create(
            {"name": "archived", "type": "consu", "is_storable": True},
        )
        template.product_variant_ids.write({"active": False})
        self.assertFalse(template.product_variant_id)

        with self.assertRaises(UserError) as caught:
            template.qty_available = 3.0

        message = str(caught.exception)
        self.assertIn("no active variant", message)
        self.assertNotIn(
            "Save the product form",
            message,
            "the template is saved; saving it again changes nothing",
        )

    def test_an_unsaved_template_is_still_told_to_save(self):
        template = self.Tmpl.new(
            {
                "name": "unsaved",
                "type": "consu",
                "is_storable": True,
                "tracking": "none",
            },
        )
        self.assertFalse(template.id)
        self.assertFalse(template.product_variant_id)
        with self.assertRaises(UserError) as caught:
            template._check_qty_available_update([3.0])
        self.assertIn("Save the product form", str(caught.exception))


@tagged("post_install", "-at_install")
class TestProductTemplateReaderScopedComputes(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Tmpl = cls.env["product.template"]
        multi_locations = cls.env.ref("stock.group_stock_multi_locations")
        stock_user = cls.env.ref("stock.group_stock_user")
        internal = cls.env.ref("base.group_user")
        cls.env.ref("base.group_user").implied_ids -= (
            multi_locations
            | cls.env.ref("stock.group_tracking_owner")
            | cls.env.ref("stock.group_tracking_lot")
        )
        cls.privileged = cls.env["res.users"].create(
            {
                "name": "advanced stock reader",
                "login": "pt_audit_advanced",
                "group_ids": [
                    (6, 0, [internal.id, stock_user.id, multi_locations.id]),
                ],
            },
        )
        cls.plain = cls.env["res.users"].create(
            {
                "name": "plain stock reader",
                "login": "pt_audit_plain",
                "group_ids": [(6, 0, [internal.id, stock_user.id])],
            },
        )

    def _assert_discriminating(self):
        self.assertTrue(
            self.Tmpl.with_user(self.privileged)._has_advanced_stock_option()
        )
        self.assertFalse(
            self.Tmpl.with_user(self.plain)._has_advanced_stock_option(),
            "something granted the advanced groups to every internal user",
        )

    def _both_orders_of(self, first, second, field_name):
        self.env.invalidate_all()
        forward = (first[field_name], second[field_name])
        self.env.invalidate_all()
        backward = (second[field_name], first[field_name])
        return forward, (backward[1], backward[0])

    def test_show_qty_update_button_is_per_reader(self):
        self._assert_discriminating()
        template = self.Tmpl.create(
            {"name": "perreader", "type": "consu", "is_storable": True},
        )
        self.env.flush_all()
        forward, backward = self._both_orders_of(
            template.with_user(self.privileged),
            template.with_user(self.plain),
            "show_qty_update_button",
        )
        self.assertEqual(forward, backward, "read order decided the answer")
        self.assertEqual(forward, (True, False))

    def test_the_variant_field_is_per_reader_too(self):
        self._assert_discriminating()
        template = self.Tmpl.create(
            {"name": "perreader2", "type": "consu", "is_storable": True},
        )
        product = template.product_variant_id
        self.env.flush_all()
        forward, backward = self._both_orders_of(
            product.with_user(self.privileged),
            product.with_user(self.plain),
            "show_qty_update_button",
        )
        self.assertEqual(forward, backward, "read order decided the answer")
        self.assertEqual(forward, (True, False))

    def _route_scoped_setup(self):
        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "Route audit B"})
        self.env["stock.route"].search([]).write({"product_selectable": False})
        self.env["stock.route"].create(
            {
                "name": "A only",
                "product_selectable": True,
                "company_id": company_a.id,
            },
        )
        template = self.Tmpl.create(
            {"name": "routescope", "type": "consu", "is_storable": True},
        )
        self.env.flush_all()
        return company_a, company_b, template

    def _both_orders(self, first, second):
        self.env.invalidate_all()
        forward = (
            first.has_available_route_ids,
            second.has_available_route_ids,
        )
        self.env.invalidate_all()
        backward = (
            second.has_available_route_ids,
            first.has_available_route_ids,
        )
        return forward, (backward[1], backward[0])

    def test_route_availability_is_not_shared_between_users(self):
        company_a, company_b, template = self._route_scoped_setup()
        internal = self.env.ref("base.group_user")
        stock_user = self.env.ref("stock.group_stock_user")
        in_a = self.env["res.users"].create(
            {
                "name": "route reader A",
                "login": "pt_audit_route_a",
                "company_id": company_a.id,
                "company_ids": [(6, 0, [company_a.id])],
                "group_ids": [(6, 0, [internal.id, stock_user.id])],
            },
        )
        in_b = self.env["res.users"].create(
            {
                "name": "route reader B",
                "login": "pt_audit_route_b",
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
                "group_ids": [(6, 0, [internal.id, stock_user.id])],
            },
        )
        forward, backward = self._both_orders(
            template.with_user(in_a),
            template.with_user(in_b),
        )
        self.assertEqual(forward, backward, "read order decided the answer")
        self.assertEqual(
            forward,
            (True, False),
            "the company-A route must be visible to A and invisible to B",
        )

    def test_route_availability_follows_a_company_switch(self):
        company_a, company_b, template = self._route_scoped_setup()
        internal = self.env.ref("base.group_user")
        stock_user = self.env.ref("stock.group_stock_user")
        reader = self.env["res.users"].create(
            {
                "name": "route reader both",
                "login": "pt_audit_route_both",
                "company_id": company_a.id,
                "company_ids": [(6, 0, [company_a.id, company_b.id])],
                "group_ids": [(6, 0, [internal.id, stock_user.id])],
            },
        )
        scoped = template.with_user(reader)
        forward, backward = self._both_orders(
            scoped.with_context(allowed_company_ids=[company_a.id]),
            scoped.with_context(allowed_company_ids=[company_b.id]),
        )
        self.assertEqual(forward, backward, "read order decided the answer")
        self.assertEqual(
            forward,
            (True, False),
            "switching to company B must hide company A's route",
        )


@tagged("post_install", "-at_install")
class TestTemplateQuantityBatching(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Tmpl = cls.env["product.template"]
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )

    def _templates(self, count, tag):
        templates = self.Tmpl.create(
            [
                {"name": f"{tag}{index}", "type": "consu", "is_storable": True}
                for index in range(count)
            ],
        )
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            [
                {
                    "product_id": template.product_variant_id.id,
                    "location_id": self.warehouse.lot_stock_id.id,
                    "inventory_quantity": 7.0,
                }
                for template in templates
            ],
        )._apply_inventory()
        self.env.flush_all()
        return templates.ids

    def _cost(self, template_ids, field_name):
        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        self.Tmpl.browse(template_ids).mapped(field_name)
        return self.env.cr.sql_statement_count - before

    def _assert_flat(self, field_name):
        small = self._templates(2, f"S{field_name}")
        large = self._templates(20, f"L{field_name}")
        self._cost(small, field_name)
        cost_small = self._cost(small, field_name)
        self._cost(large, field_name)
        cost_large = self._cost(large, field_name)
        self.assertEqual(
            cost_large,
            cost_small,
            f"{field_name} costs {cost_large} queries for 20 templates against "
            f"{cost_small} for 2 -- the variant prefetch set stopped batching it",
        )

    def test_qty_available_is_flat_in_the_number_of_templates(self):
        self._assert_flat("qty_available")

    def test_count_moves_in_is_flat_in_the_number_of_templates(self):
        self._assert_flat("count_moves_in")

    def test_count_lot_ids_is_flat_in_the_number_of_templates(self):
        self._assert_flat("count_lot_ids")
