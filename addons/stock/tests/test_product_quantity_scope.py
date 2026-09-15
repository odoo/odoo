import datetime

from odoo import fields
from odoo.exceptions import RedirectWarning, UserError
from odoo.fields import Domain
from odoo.tests import TransactionCase, tagged

from odoo.addons.stock.models.product_product_quantity import (
    ProductProductQuantity as StockProductProduct,
)
from odoo.addons.stock.tools.quantity import (
    QuantityFilters,
    get_context_record_ids,
)


@tagged("post_install", "-at_install")
class TestProductQuantityScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.product = cls.env["product.product"].create(
            {"name": "Scope Test Product", "is_storable": True, "type": "consu"},
        )

    def _stock_up(self, product, qty, location=None):
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": product.id,
                "location_id": (location or self.stock_location).id,
                "inventory_quantity": qty,
            }
        )._apply_inventory()

    def test_boolean_location_context_is_rejected_in_python(self):
        for key in ("location", "warehouse_id", "search_location", "search_warehouse"):
            with self.subTest(context_key=key):
                with self.assertRaises(ValueError):
                    self.product.with_context(**{key: True}).qty_available

    def test_unresolvable_location_context_never_raises_missing_error(self):
        self._stock_up(self.product, 7)
        self.assertEqual(self.product.qty_available, 7)
        cases = (
            {"location": "No Such Location"},
            {"location": 999_999_999},
            {"warehouse_id": 999_999_999},
            {"warehouse_id": self.warehouse.id, "location": 999_999_999},
            {"warehouse_id": 999_999_999, "location": self.stock_location.id},
        )
        for context in cases:
            with self.subTest(context=context):
                product = self.product.with_context(**context)
                product.invalidate_recordset()
                self.assertEqual(product.qty_available, 0.0)

    def test_valid_location_context_still_resolves(self):
        self._stock_up(self.product, 7)
        for context in (
            {"location": self.stock_location.id},
            {"location": self.stock_location.name},
            {"warehouse_id": self.warehouse.id},
        ):
            with self.subTest(context=context):
                product = self.product.with_context(**context)
                product.invalidate_recordset()
                self.assertEqual(product.qty_available, 7.0)

    def test_no_model_still_carries_the_scope_under_its_old_name(self):
        gone = (
            "_get_domain_locations",
            "_get_domain_locations_new",
            "_scope_location_ids",
            "_resolve_context_record_ids",
        )
        offenders = [
            f"{model_name}.{name}"
            for model_name, Model in self.env.registry.items()
            for name in gone
            if hasattr(Model, name)
        ]
        self.assertFalse(
            offenders,
            "the scope lives on stock.location as _get_domains_quantity / "
            "_get_domains_quantity_from_context / _resolve_scope_ids_from_context, and "
            "get_context_record_ids is a function in stock.tools.quantity; "
            "these are stale and are never called: " + ", ".join(offenders),
        )
        Location = type(self.env["stock.location"])
        for name in (
            "_get_domains_quantity",
            "_get_domains_quantity_from_context",
            "_resolve_scope_ids_from_context",
        ):
            self.assertTrue(hasattr(Location, name), f"stock.location lost {name}")

    def test_strict_scope_already_skips_in_progress(self):
        Location = self.env["stock.location"]
        location_ids = self.stock_location.ids
        strict = Location.with_context(strict=True)._get_domains_quantity(location_ids)
        strict_skipping = Location.with_context(
            strict=True, skip_in_progress=True
        )._get_domains_quantity(location_ids)
        self.assertEqual(repr(strict), repr(strict_skipping))
        self.assertNotIn("location_final_id", repr(strict))
        plain = Location._get_domains_quantity(location_ids)
        skipping = Location.with_context(skip_in_progress=True)._get_domains_quantity(
            location_ids
        )
        self.assertIn("location_final_id", repr(plain))
        self.assertNotIn("location_final_id", repr(skipping))

    def test_inverse_qty_available_uses_the_products_own_company(self):
        company_b = self.env["res.company"].create({"name": "Scope Co B"})
        warehouse_b = self.env["stock.warehouse"].search(
            [("company_id", "=", company_b.id)], limit=1
        ) or self.env["stock.warehouse"].create(
            {"name": "Scope WH B", "code": "SWB", "company_id": company_b.id}
        )
        product_b = self.env["product.product"].create(
            {
                "name": "Scope Co B Product",
                "is_storable": True,
                "type": "consu",
                "company_id": company_b.id,
            }
        )
        self.assertNotEqual(self.env.company, company_b)
        product_b.with_context(
            allowed_company_ids=[self.env.company.id, company_b.id]
        ).qty_available = 3.0
        product_b.flush_recordset()
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", product_b.id),
                ("location_id.usage", "=", "internal"),
            ]
        )
        self.assertEqual(quant.location_id, warehouse_b.lot_stock_id)
        self.assertEqual(quant.company_id, company_b)

    def test_inverse_qty_available_batches_two_companies_at_once(self):
        company_b = self.env["res.company"].create({"name": "Scope Co B2"})
        warehouse_b = self.env["stock.warehouse"].search(
            [("company_id", "=", company_b.id)], limit=1
        ) or self.env["stock.warehouse"].create(
            {"name": "Scope WH B2", "code": "SB2", "company_id": company_b.id}
        )
        product_b = self.env["product.product"].create(
            {
                "name": "Scope B2 Product",
                "is_storable": True,
                "type": "consu",
                "company_id": company_b.id,
            }
        )
        products = self.product | product_b
        products.with_context(
            allowed_company_ids=[self.env.company.id, company_b.id]
        ).qty_available = 5.0
        products.flush_recordset()
        by_product = {
            quant.product_id: quant.location_id
            for quant in self.env["stock.quant"].search(
                [
                    ("product_id", "in", products.ids),
                    ("location_id.usage", "=", "internal"),
                ]
            )
        }
        self.assertEqual(by_product[self.product], self.stock_location)
        self.assertEqual(by_product[product_b], warehouse_b.lot_stock_id)

    def test_inverse_qty_available_still_refuses_negative(self):
        with self.assertRaises(UserError):
            self.product.qty_available = -1.0
            self.product.flush_recordset()

    def test_count_moves_is_invalidated_by_a_receipt(self):
        self.assertEqual(self.product.count_moves_in, 0)
        supplier = self.env.ref("stock.stock_location_suppliers")
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming"), ("warehouse_id", "=", self.warehouse.id)],
            limit=1,
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": supplier.id,
                "location_dest_id": self.stock_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 4,
                            "location_id": supplier.id,
                            "location_dest_id": self.stock_location.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.move_ids.quantity = 4
        picking.button_validate()
        self.assertEqual(self.product.count_moves_in, 1)

    def test_count_lot_ids_is_invalidated_by_a_new_lot(self):
        tracked = self.env["product.product"].create(
            {
                "name": "Scope Tracked",
                "is_storable": True,
                "type": "consu",
                "tracking": "lot",
            }
        )
        self.assertEqual(tracked.count_lot_ids, 0)
        self.env["stock.lot"].create({"name": "SCOPE-L1", "product_id": tracked.id})
        self.assertEqual(tracked.count_lot_ids, 1)

    def test_count_reordering_rules_is_invalidated_by_a_new_rule(self):
        self.assertEqual(self.product.count_reordering_rules, 0)
        self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product.id,
                "warehouse_id": self.warehouse.id,
                "location_id": self.stock_location.id,
                "product_min_qty": 2,
                "product_max_qty": 9,
            }
        )
        self.assertEqual(self.product.count_reordering_rules, 1)
        self.assertEqual(self.product.reordering_qty_min, 2)
        self.assertEqual(self.product.reordering_qty_max, 9)

    def test_filter_to_unlink_excludes_products_the_database_will_refuse(self):
        with_stock = self.env["product.product"].create(
            {"name": "Scope Stocked", "is_storable": True, "type": "consu"}
        )
        self._stock_up(with_stock, 5)
        clean = self.env["product.product"].create(
            {"name": "Scope Clean", "is_storable": True, "type": "consu"}
        )
        unlinkable = (with_stock | clean)._filtered_to_unlink()
        self.assertIn(clean, unlinkable)
        self.assertNotIn(with_stock, unlinkable)

    def test_unlink_or_archive_archives_a_product_with_stock(self):
        with_stock = self.env["product.product"].create(
            {"name": "Scope Stocked 2", "is_storable": True, "type": "consu"}
        )
        self._stock_up(with_stock, 5)
        with_stock._unlink_or_archive()
        self.assertTrue(with_stock.exists())
        self.assertFalse(with_stock.active)

    def test_get_picking_description_declares_its_singleton(self):
        other = self.env["product.product"].create(
            {"name": "Scope Other", "is_storable": True, "type": "consu"}
        )
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        with self.assertRaises(ValueError):
            (self.product | other)._get_picking_description(picking_type)

    def test_action_view_orderpoints_tolerates_an_empty_context(self):
        action = self.env.ref("stock.action_orderpoint")
        for context in ("{'search_default_trigger': 'auto'}", "{}", ""):
            with self.subTest(context=context):
                action.context = context
                result = self.product.action_view_orderpoints()
                self.assertIsInstance(result["context"], dict)
                self.assertNotIn("search_default_trigger", result["context"])
                self.assertTrue(result["context"]["search_default_filter_not_snoozed"])

    def test_prepare_quantities_scope_carries_the_dates_without_reading(self):
        location_domains = self.env[
            "stock.location"
        ]._get_domains_quantity_from_context()
        self.env.flush_all()
        past = fields.Datetime.now() - datetime.timedelta(days=5)
        queries_before = self.env.cr.sql_statement_count
        scope = self.product._prepare_quantities_scope(
            QuantityFilters(to_date=past), location_domains=location_domains
        )
        self.assertEqual(
            self.env.cr.sql_statement_count,
            queries_before,
            "assembling the scope must not hit the database",
        )
        self.assertTrue(scope.dates_in_the_past)
        self.assertIsNone(scope.expired_quant)
        self.assertNotEqual(scope.move_in_done, Domain.FALSE)

        future = fields.Datetime.now() + datetime.timedelta(days=5)
        scope = self.product._prepare_quantities_scope(
            QuantityFilters(to_date=future), location_domains=location_domains
        )
        self.assertFalse(scope.dates_in_the_past)
        self.assertEqual(scope.move_in_done, Domain.FALSE)
        self.assertEqual(scope.move_out_done, Domain.FALSE)

    def test_stocks_own_expiry_hook_narrows_on_nothing(self):
        scoped = self.product.with_context(
            with_expiration=datetime.date.today(),
            fresh_qty_forecast=True,
        )
        self.assertIsNone(
            StockProductProduct._get_expired_quant_domain_at_date(
                scoped, Domain.TRUE, None
            ),
            "stock alone must not narrow on a column it does not define",
        )

    def test_normalize_to_date_widens_a_bare_date_to_the_readers_whole_day(self):
        Product = self.env["product.product"]
        day = datetime.date(2020, 1, 15)

        utc = Product.with_context(tz="UTC")
        normalized, in_the_past = utc._normalize_quantities_to_date(day)
        self.assertTrue(in_the_past)
        self.assertEqual(normalized.date(), day)
        self.assertEqual((normalized.hour, normalized.minute), (23, 59))

        for tz, expected in (
            ("America/Mexico_City", datetime.datetime(2020, 1, 16, 5, 59, 59)),
            ("Pacific/Auckland", datetime.datetime(2020, 1, 15, 10, 59, 59)),
        ):
            with self.subTest(tz=tz):
                scoped = Product.with_context(tz=tz)
                for value in (day, "2020-01-15"):
                    normalized, __ = scoped._normalize_quantities_to_date(value)
                    self.assertEqual(
                        normalized.replace(microsecond=0),
                        expected,
                        f"{value!r} must end the reader's day, not UTC's",
                    )

        normalized, in_the_past = Product._normalize_quantities_to_date(False)
        self.assertFalse(normalized)
        self.assertFalse(in_the_past)

    def test_prepare_quantities_vals_accepts_preresolved_location_domains(self):
        self._stock_up(self.product, 6)
        Product = self.env["product.product"]
        location_domains = self.env[
            "stock.location"
        ]._get_domains_quantity_from_context()
        vals = self.product._prepare_quantities_vals(
            QuantityFilters(), location_domains=location_domains
        )
        self.assertEqual(vals[self.product.id]["qty_available"], 6.0)
        candidates = Product._get_quantity_search_candidates(
            location_domains=location_domains
        )
        self.assertIn(self.product, candidates)

    def test_quantity_search_resolves_location_domains_once_per_condition(self):
        self._stock_up(self.product, 6)
        Product = self.env["product.product"]
        cls = type(self.env["stock.location"])
        calls = []
        original = cls._get_domains_quantity_from_context

        def counting(records):
            calls.append(1)
            return original(records)

        cls._get_domains_quantity_from_context = counting
        try:
            Product.search([("qty_free", ">", 0)])
        finally:
            cls._get_domains_quantity_from_context = original
        self.assertEqual(
            len(calls),
            1,
            "the location triple should be resolved once per quantity condition",
        )

    def test_get_context_record_ids_accepts_ids_and_names(self):
        def resolve(model, values):
            return get_context_record_ids(self.env, model, values)

        self.assertEqual(
            resolve("stock.location", [self.stock_location.id]),
            {self.stock_location.id},
        )
        self.assertIn(
            self.stock_location.id,
            resolve("stock.location", [self.stock_location.name]),
        )
        self.assertEqual(resolve("stock.location", [999_999_999]), set())
        self.assertEqual(resolve("stock.location", ["No Such Location"]), set())

    def test_get_context_record_ids_rejects_booleans(self):
        def resolve(model, values):
            return get_context_record_ids(self.env, model, values)

        for value in (True, False):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve("stock.location", [value])

    def test_narrow_quantity_domains_leaves_unfiltered_domains_alone(self):
        product = self.env["product.product"]
        base = (Domain.TRUE, Domain.TRUE, Domain.TRUE)
        untouched = product._narrow_quantity_domains(*base, QuantityFilters())
        self.assertEqual([repr(d) for d in untouched], [repr(d) for d in base])
        quant, move_in, __ = product._narrow_quantity_domains(
            *base, QuantityFilters(lot_id=False)
        )
        self.assertIn("lot_id", repr(quant))
        self.assertIn("move_line_ids.lot_id", repr(move_in))

    def test_location_scope_covers_children(self):
        child = self.env["stock.location"].create(
            {"name": "Scope Child", "location_id": self.stock_location.id}
        )
        product = self.env["product.product"].create(
            {"name": "Scope Child Product", "is_storable": True, "type": "consu"}
        )
        self._stock_up(product, 4, location=child)
        self.assertEqual(
            product.with_context(location=self.stock_location.id).qty_available, 4.0
        )
        product.invalidate_recordset()
        self.assertEqual(
            product.with_context(
                location=self.stock_location.id, strict=True
            ).qty_available,
            0.0,
        )

    def _quantity_dependency_cases(self):
        Quant = self.env["stock.quant"]
        Move = self.env["stock.move"]
        shelf = self.env["stock.location"].create(
            {"name": "Dep Shelf", "location_id": self.stock_location.id},
        )
        customers = self.env.ref("stock.stock_location_customers")
        suppliers = self.env.ref("stock.stock_location_suppliers")

        def product(name, **kw):
            return self.env["product.product"].create(
                {"name": name, "is_storable": True, "type": "consu", **kw},
            )

        def quant(prod, qty, **kw):
            return Quant.create(
                {
                    "product_id": prod.id,
                    "location_id": self.stock_location.id,
                    "quantity": qty,
                    **kw,
                },
            )

        cases = []

        p_qty = product("Dep qty")
        q_qty = quant(p_qty, 4.0)
        cases.append(
            (
                "quant.quantity",
                p_qty,
                {},
                "qty_available",
                lambda: q_qty.write({"quantity": 9.0}),
                9.0,
            )
        )

        p_res = product("Dep reserved")
        q_res = quant(p_res, 4.0)
        cases.append(
            (
                "quant.reserved_quantity",
                p_res,
                {},
                "qty_free",
                lambda: q_res.write({"reserved_quantity": 1.0}),
                3.0,
            )
        )

        p_loc = product("Dep location")
        q_loc = quant(p_loc, 4.0)
        cases.append(
            (
                "quant.location_id, out of scope",
                p_loc,
                {},
                "qty_available",
                lambda: q_loc.write({"location_id": customers.id}),
                0.0,
            )
        )

        p_new = product("Dep new quant")
        quant(p_new, 4.0)
        cases.append(
            (
                "a second quant created",
                p_new,
                {},
                "qty_available",
                lambda: quant(p_new, 6.0, location_id=shelf.id),
                10.0,
            )
        )

        p_del = product("Dep unlink")
        q_del = quant(p_del, 4.0)
        quant(p_del, 6.0, location_id=shelf.id)
        cases.append(
            ("a quant unlinked", p_del, {}, "qty_available", q_del.unlink, 6.0)
        )

        p_lot = product("Dep lot", tracking="lot")
        lot_a = self.env["stock.lot"].create(
            {"name": "DEP-A", "product_id": p_lot.id},
        )
        lot_b = self.env["stock.lot"].create(
            {"name": "DEP-B", "product_id": p_lot.id},
        )
        q_lot = quant(p_lot, 8.0, lot_id=lot_a.id)
        cases.append(
            (
                "quant.lot_id under ctx lot_id",
                p_lot,
                {"lot_id": lot_a.id},
                "qty_available",
                lambda: q_lot.write({"lot_id": lot_b.id}),
                0.0,
            )
        )

        owner = self.env["res.partner"].create({"name": "Dep Owner"})
        p_own = product("Dep owner")
        q_own = quant(p_own, 3.0, owner_id=owner.id)
        cases.append(
            (
                "quant.owner_id under ctx owner_id",
                p_own,
                {"owner_id": owner.id},
                "qty_available",
                lambda: q_own.write({"owner_id": False}),
                0.0,
            )
        )

        package = self.env["stock.package"].create({})
        p_pkg = product("Dep package")
        q_pkg = quant(p_pkg, 3.0, package_id=package.id)
        cases.append(
            (
                "quant.package_id under ctx package_id",
                p_pkg,
                {"package_id": package.id},
                "qty_available",
                lambda: q_pkg.write({"package_id": False}),
                0.0,
            )
        )

        def move(prod, src, dest, qty=5.0, **kw):
            rec = Move.create(
                {
                    "product_id": prod.id,
                    "product_uom_qty": qty,
                    "location_id": src.id,
                    "location_dest_id": dest.id,
                    **kw,
                },
            )
            rec._action_confirm()
            return rec

        p_in = product("Dep incoming")
        m_in = move(p_in, suppliers, shelf)
        cases.append(
            (
                "move.location_dest_id, out of scope",
                p_in,
                {},
                "qty_incoming",
                lambda: m_in.write({"location_dest_id": customers.id}),
                0.0,
            )
        )

        p_fin = product("Dep final")
        m_fin = move(p_fin, suppliers, shelf)
        cases.append(
            (
                "move.location_final_id, out of scope",
                p_fin,
                {},
                "qty_incoming",
                lambda: m_fin.write({"location_final_id": customers.id}),
                0.0,
            )
        )

        p_out = product("Dep outgoing")
        m_out = move(p_out, shelf, customers, qty=4.0)
        cases.append(
            (
                "move.location_id, out of scope",
                p_out,
                {},
                "qty_outgoing",
                lambda: m_out.write({"location_id": customers.id}),
                0.0,
            )
        )

        p_date = product("Dep date")
        soon = fields.Datetime.now() + datetime.timedelta(days=1)
        far = fields.Datetime.now() + datetime.timedelta(days=40)
        m_date = move(p_date, suppliers, shelf, qty=7.0)
        m_date.date = soon
        window = {"to_date": fields.Datetime.now() + datetime.timedelta(days=7)}
        cases.append(
            (
                "move.date, pushed past to_date",
                p_date,
                window,
                "qty_incoming",
                lambda: m_date.write({"date": far}),
                0.0,
            )
        )

        self.env.flush_all()
        return cases

    def test_every_scope_field_invalidates_the_quantity_fields(self):
        stale = []
        for (
            label,
            product,
            context,
            field,
            mutate,
            expected,
        ) in self._quantity_dependency_cases():
            with self.subTest(dependency=label):
                scoped = product.with_context(**context)
                scoped[field]
                mutate()
                got = scoped[field]
                if abs(got - expected) > 1e-6:
                    stale.append(f"{label}: {field} read {got}, expected {expected}")
                self.assertAlmostEqual(
                    got,
                    expected,
                    msg=f"{label!r} did not invalidate {field}",
                )
        self.assertFalse(stale, "\n".join(stale))

    def test_a_package_scope_narrows_the_flows_as_well_as_the_stock(self):
        package = self.env["stock.package"].create({})
        product = self.env["product.product"].create(
            {"name": "Scope Package Product", "is_storable": True, "type": "consu"},
        )
        self.env["stock.quant"].create(
            [
                {
                    "product_id": product.id,
                    "location_id": self.stock_location.id,
                    "quantity": 10.0,
                    "package_id": package.id,
                },
                {
                    "product_id": product.id,
                    "location_id": self.stock_location.id,
                    "quantity": 5.0,
                },
            ],
        )
        self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 3.0,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.stock_location.id,
            },
        )._action_confirm()
        self.env.flush_all()

        unscoped = product.with_context(package_id=None)
        self.assertEqual(unscoped.qty_available, 15.0)
        self.assertEqual(unscoped.qty_incoming, 3.0)
        self.assertEqual(unscoped.qty_available_virtual, 18.0)

        scoped = product.with_context(package_id=package.id)
        scoped.invalidate_recordset()
        self.assertEqual(scoped.qty_available, 10.0)
        self.assertEqual(
            scoped.qty_incoming,
            0.0,
            "nothing is on its way into this package",
        )
        self.assertEqual(
            scoped.qty_available_virtual,
            10.0,
            "the forecast must not add stock arriving outside the scope it reports",
        )

    def test_the_missing_warehouse_warning_names_the_company_that_lacks_one(self):
        company_b = self.env["res.company"].create({"name": "Scope Co No WH"})
        self.env["stock.warehouse"].search(
            [("company_id", "=", company_b.id)],
        ).unlink()
        self.env.user.company_ids |= company_b
        self.env.user.group_ids |= self.env.ref("stock.group_stock_manager")
        product = self.env["product.product"].create(
            {
                "name": "Scope MC Product",
                "is_storable": True,
                "type": "consu",
                "company_id": company_b.id,
            },
        )
        scoped = product.with_context(
            allowed_company_ids=[self.env.company.id, company_b.id],
        )
        self.assertEqual(
            scoped.env.company,
            self.env.company,
            "the active company must stay the one that does have a warehouse",
        )
        with self.assertRaises(RedirectWarning) as caught:
            scoped.qty_available = 5.0
        message = str(caught.exception)
        self.assertIn(company_b.display_name, message)
        self.assertNotIn(self.env.company.display_name, message)

    def test_a_false_lot_id_in_the_context_narrows_read_and_search_alike(self):
        product = self.env["product.product"].create(
            {
                "name": "Scope Lot Product",
                "is_storable": True,
                "type": "consu",
                "tracking": "lot",
            },
        )
        lot = self.env["stock.lot"].create(
            {"name": "SCOPE-L1", "product_id": product.id},
        )
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": product.id,
                "location_id": self.stock_location.id,
                "lot_id": lot.id,
                "inventory_quantity": 8,
            }
        )._apply_inventory()

        Product = self.env["product.product"].with_context(lot_id=False)
        self.assertEqual(
            product.with_context(lot_id=False).qty_available,
            0.0,
            "the only stock is under a lot, so the unlotted scope holds nothing",
        )
        self.assertNotIn(
            product.id,
            Product.search([("id", "=", product.id), ("qty_available", ">", 0)]).ids,
            "the search must agree with the read it is the search for",
        )
        self.assertIn(
            product.id,
            Product.search([("id", "=", product.id), ("qty_available", "<", 1)]).ids,
        )
        self.assertEqual(
            product.with_context(lot_id=lot.id).qty_available,
            8.0,
            "and naming the lot must still find it",
        )

    def test_inverse_qty_available_lands_in_the_scoped_warehouse(self):
        warehouse_b = self.env["stock.warehouse"].create(
            {"name": "Scope WH2", "code": "SW2", "company_id": self.env.company.id}
        )
        scoped = self.product.with_context(warehouse_id=warehouse_b.id)
        self.assertEqual(scoped.qty_available, 0.0)
        scoped.qty_available = 9.0
        self.product.flush_recordset()
        self.env.invalidate_all()
        self.assertEqual(
            self.product.with_context(warehouse_id=warehouse_b.id).qty_available,
            9.0,
            "the value must read back through the scope it was written under",
        )
        self.assertEqual(
            self.product.with_context(warehouse_id=self.warehouse.id).qty_available,
            0.0,
            "and must not have landed in the unscoped warehouse",
        )

    def test_inverse_qty_available_lands_in_the_scoped_location(self):
        shelf = self.env["stock.location"].create(
            {
                "name": "Scope Shelf",
                "location_id": self.stock_location.id,
                "usage": "internal",
            }
        )
        scoped = self.product.with_context(location=shelf.id)
        scoped.qty_available = 4.0
        self.product.flush_recordset()
        self.env.invalidate_all()
        quant = self.env["stock.quant"].search(
            [("product_id", "=", self.product.id), ("location_id", "=", shelf.id)]
        )
        self.assertEqual(quant.quantity, 4.0)
        self.assertEqual(
            self.product.with_context(location=shelf.id).qty_available, 4.0
        )

    def test_inverse_qty_available_refuses_an_ambiguous_scope(self):
        shelf_a = self.env["stock.location"].create(
            {
                "name": "Scope Shelf A",
                "location_id": self.stock_location.id,
                "usage": "internal",
            }
        )
        shelf_b = self.env["stock.location"].create(
            {
                "name": "Scope Shelf B",
                "location_id": self.stock_location.id,
                "usage": "internal",
            }
        )
        with self.assertRaises(UserError):
            self.product.with_context(
                location=[shelf_a.id, shelf_b.id]
            ).qty_available = 5.0

    def test_inverse_qty_available_without_a_scope_still_uses_the_warehouse(self):
        self.product.qty_available = 6.0
        self.product.flush_recordset()
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product.id),
                ("location_id.usage", "=", "internal"),
            ]
        )
        self.assertEqual(quant.location_id, self.warehouse.lot_stock_id)

    def test_count_moves_follows_the_move_line_not_the_move(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.stock_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 5,
                            "location_id": self.env.ref(
                                "stock.stock_location_suppliers"
                            ).id,
                            "location_dest_id": self.stock_location.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.move_ids.quantity = 5
        picking.button_validate()
        self.assertEqual(self.product.count_moves_in, 1)
        self.env["stock.move.line"].search(
            [("product_id", "=", self.product.id)]
        ).write({"date": "2020-01-01 00:00:00"})
        self.assertEqual(
            self.product.count_moves_in,
            0,
            "ageing the move line out of the 12-month window must invalidate",
        )

    def test_template_count_moves_is_invalidated_by_a_receipt(self):
        template = self.product.product_tmpl_id
        self.assertEqual(template.count_moves_in, 0)
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.stock_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 3,
                            "location_id": self.env.ref(
                                "stock.stock_location_suppliers"
                            ).id,
                            "location_dest_id": self.stock_location.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.move_ids.quantity = 3
        picking.button_validate()
        self.assertEqual(template.count_moves_in, 1)
        self.assertEqual(
            template.count_moves_in,
            self.product.count_moves_in,
            "the template rolls the variant counters up, so they cannot disagree",
        )

    def test_template_quantity_search_resolves_location_domains_once(self):
        self._stock_up(self.product, 6)
        cls = type(self.env["stock.location"])
        calls = []
        original = cls._get_domains_quantity_from_context

        def counting(records):
            calls.append(1)
            return original(records)

        cls._get_domains_quantity_from_context = counting
        try:
            self.env["product.template"].search([("qty_available_virtual", ">", 0)])
        finally:
            cls._get_domains_quantity_from_context = original
        self.assertEqual(
            len(calls),
            1,
            "the location triple should be resolved once per quantity condition",
        )

    def test_falsy_date_context_keeps_the_quant_only_fast_path(self):
        self._stock_up(self.product, 5)
        cls = type(self.env["product.product"])
        slow_path = []
        original = cls._get_domain_product_quantity

        def counting(records, operator, value, field):
            slow_path.append(field)
            return original(records, operator, value, field)

        cls._get_domain_product_quantity = counting
        try:
            found = (
                self.env["product.product"]
                .with_context(to_date=False, from_date=False)
                .search([("id", "=", self.product.id), ("qty_available", ">", 0)])
            )
        finally:
            cls._get_domain_product_quantity = original
        self.assertEqual(found, self.product)
        self.assertFalse(slow_path, "a falsy date must not abandon the quant-only path")

    def test_owners_context_still_takes_the_slow_path_when_empty(self):
        self._stock_up(self.product, 5)
        cls = type(self.env["product.product"])
        slow_path = []
        original = cls._get_domain_product_quantity

        def counting(records, operator, value, field):
            slow_path.append(field)
            return original(records, operator, value, field)

        cls._get_domain_product_quantity = counting
        try:
            self.env["product.product"].with_context(owners=[]).search(
                [("id", "=", self.product.id), ("qty_available", ">", 0)]
            )
        finally:
            cls._get_domain_product_quantity = original
        self.assertTrue(slow_path, "an owner filter must still take the full pass")

    def test_fields_get_relabels_a_location_given_by_name_or_list(self):
        customers = self.env.ref("stock.stock_location_customers")
        Product = self.env["product.product"]
        expected = Product.with_context(location=customers.id).fields_get(
            ["qty_available"]
        )["qty_available"]["string"]
        for value in (customers.id, [customers.id], customers.name):
            with self.subTest(location=value):
                self.assertEqual(
                    Product.with_context(location=value).fields_get(["qty_available"])[
                        "qty_available"
                    ]["string"],
                    expected,
                )

    def test_fields_get_survives_an_unresolvable_location(self):
        Product = self.env["product.product"]
        for value in (True, 99999999, "No Such Location"):
            with self.subTest(location=value):
                res = Product.with_context(location=value).fields_get(["qty_available"])
                self.assertTrue(res["qty_available"]["string"])


class TestTemplateQuantitySearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.product = cls.env["product.product"].create(
            {"name": "Template Search Product", "is_storable": True, "type": "consu"},
        )
        cls.template = cls.product.product_tmpl_id
        cls.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": cls.product.id,
                "location_id": cls.stock_location.id,
                "inventory_quantity": 7,
            }
        )._apply_inventory()

    QUANTITY_FIELDS = (
        "qty_available",
        "qty_available_virtual",
        "qty_incoming",
        "qty_outgoing",
    )

    def test_every_quantity_field_is_searchable_on_a_template(self):
        Template = self.env["product.template"]
        for field_name in self.QUANTITY_FIELDS:
            with self.subTest(field=field_name):
                Template.search([(field_name, ">", 0)])

    def test_a_template_search_finds_the_stocked_template(self):
        found = self.env["product.template"].search([("qty_available", ">", 0)])
        self.assertIn(self.template, found)

    def test_a_template_search_agrees_with_its_variant(self):
        for operator, value in ((">", 0), (">=", 7), ("<", 8), ("=", 7)):
            with self.subTest(operator=operator, value=value):
                templates = self.env["product.template"].search(
                    [("qty_available", operator, value)]
                )
                products = self.env["product.product"].search(
                    [("qty_available", operator, value)]
                )
                self.assertEqual(
                    self.template in templates,
                    self.product in products,
                    f"template and variant disagree on qty_available "
                    f"{operator} {value}",
                )

    def test_zero_matching_templates_are_included_when_the_operator_admits_zero(self):
        empty = self.env["product.product"].create(
            {"name": "Nothing In Scope", "is_storable": True, "type": "consu"}
        )
        found = self.env["product.template"].search([("qty_available", "<=", 0)])
        self.assertIn(empty.product_tmpl_id, found)
        self.assertNotIn(self.template, found)

    def test_a_set_operator_is_answered_in_python(self):
        found = self.env["product.template"].search([("qty_available", "in", [7])])
        self.assertIn(self.template, found)
