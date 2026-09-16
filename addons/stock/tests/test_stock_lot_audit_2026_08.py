from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tests import TransactionCase


class TestLotNameFormatVocabulary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Lot = cls.env["stock.lot"]

    def _product(self, lot_name_format):
        return self.env["product.product"].create(
            {
                "name": "Formatted %s" % lot_name_format,
                "is_storable": True,
                "tracking": "lot",
                "lot_name_format": lot_name_format,
            }
        )

    def test_every_parsed_placeholder_family_also_composes(self):
        placeholders = set(self.Lot._get_lot_name_placeholders()) - {"ref"}
        self.assertGreater(len(placeholders), 14, "the three families are expected")
        for placeholder in sorted(placeholders):
            with self.subTest(placeholder=placeholder):
                product = self._product("%%(%s)s-X" % placeholder)
                lot = self.Lot.create({"product_id": product.id})
                self.assertTrue(lot.name.endswith("-X"))

    def test_a_composed_name_parses_back_for_every_family(self):
        for placeholder in ("year", "current_year", "range_month"):
            with self.subTest(placeholder=placeholder):
                product = self._product("%%(%s)s-%%(ref)s" % placeholder)
                lot = self.Lot.create({"product_id": product.id})
                self.assertIn(placeholder, lot._parse_name() or {})

    def test_an_unusable_format_is_a_message_not_a_traceback(self):
        for lot_format in ("100%-%(ref)s", "%(bogus)s", "%(ref)"):
            with self.subTest(lot_format=lot_format):
                product = self._product(lot_format)
                with self.assertRaises(UserError) as caught:
                    self.Lot.create({"product_id": product.id})
                self.assertIn(product.display_name, str(caught.exception))

    def test_reading_a_name_back_under_a_broken_format_does_not_raise(self):
        product = self._product("%(year)s-%(ref)s")
        lot = self.Lot.create({"product_id": product.id})
        product.lot_name_format = "%(bogus)s"
        self.assertIsNone(lot._parse_name())

    def test_a_product_with_no_sequence_at_all_says_so(self):
        product = self.env["product.product"].create(
            {"name": "Sequenceless", "is_storable": True, "tracking": "lot"}
        )
        product.lot_sequence_id = False
        self.env["ir.sequence"].search([("code", "=", "stock.lot.serial")]).unlink()
        with self.assertRaises(UserError) as caught:
            self.Lot.create({"product_id": product.id})
        self.assertIn(product.display_name, str(caught.exception))


class TestLotUniquenessSeesArchivedLots(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Lot = cls.env["stock.lot"]
        cls.product = cls.env["product.product"].create(
            {"name": "Archivable", "is_storable": True, "tracking": "serial"}
        )

    def test_an_archived_lot_still_holds_its_name(self):
        archived = self.Lot.create({"name": "SN00010", "product_id": self.product.id})
        archived.active = False
        self.env.flush_all()
        with self.assertRaises(ValidationError):
            self.Lot.create({"name": "SN00010", "product_id": self.product.id})

    def test_the_cross_company_rule_sees_archived_lots(self):
        archived = self.Lot.create(
            {"name": "SNX", "product_id": self.product.id, "company_id": False}
        )
        archived.active = False
        self.env.flush_all()
        with self.assertRaises(ValidationError):
            self.Lot.create(
                {
                    "name": "SNX",
                    "product_id": self.product.id,
                    "company_id": self.env.company.id,
                }
            )

    def test_un_archiving_re_checks_the_rule(self):
        archived = self.Lot.create(
            {"name": "SNY", "product_id": self.product.id, "company_id": False}
        )
        archived.active = False
        self.env.flush_all()
        self.env.cr.execute(
            """INSERT INTO stock_lot
               (name, product_id, company_id, active, create_uid, write_uid, create_date, write_date)
               VALUES ('SNY', %s, %s, true, 1, 1, now(), now())""",
            (self.product.id, self.env.company.id),
        )
        self.env.invalidate_all()
        with self.assertRaises(ValidationError):
            archived.active = True
            self.env.flush_all()

    def test_the_next_serial_is_one_nothing_holds(self):
        for name in ("SN00001", "SN00002", "SN00003"):
            self.Lot.create({"name": name, "product_id": self.product.id})
        archived = self.Lot.create({"name": "SN00004", "product_id": self.product.id})
        archived.active = False
        self.env.flush_all()
        proposed = self.Lot._get_next_serial(self.env.company, self.product)
        self.assertNotEqual(proposed, "SN00004", "the archived lot holds that name")
        self.Lot.create({"name": proposed, "product_id": self.product.id})
        self.env.flush_all()

    def test_the_next_serial_survives_an_out_of_order_import(self):
        """The guarantee is that the proposal is FREE, not that it is highest.

        `_get_next_serial` reads the most recently *created* lot
        (`order="id DESC"`), not the highest-named one, so importing an old
        serial after a newer block moves the proposal back to the low range --
        SN00002 here, not SN00052. That is deliberate and matches upstream;
        uniqueness is what `_get_free_lot_name` guarantees, by walking forward
        until the name is free. This test asserted neither, so a change from
        "most recent" to "highest" would have passed it silently.
        """
        for name in ("SN00050", "SN00051"):
            self.Lot.create({"name": name, "product_id": self.product.id})
        self.Lot.create({"name": "SN00001", "product_id": self.product.id})
        self.env.flush_all()

        proposed = self.Lot._get_next_serial(self.env.company, self.product)

        self.assertEqual(
            proposed, "SN00002", "the proposal follows the most recent lot"
        )
        self.assertFalse(
            self.Lot.with_context(active_test=False).search_count(
                [("name", "=", proposed), ("product_id", "=", self.product.id)]
            ),
            "the proposal must be free before it is offered",
        )
        created = self.Lot.create({"name": proposed, "product_id": self.product.id})
        self.env.flush_all()
        self.assertEqual(created.name, proposed)

    def test_prepare_next_lot_vals_is_the_one_place_that_decides(self):
        vals = self.Lot._prepare_next_lot_vals(self.env.company, self.product)
        self.assertEqual(vals["product_id"], self.product.id)
        self.Lot.create(vals)
        self.env.flush_all()
        self.Lot.create(self.Lot._prepare_next_lot_vals(self.env.company, self.product))
        self.env.flush_all()


class TestLotUniquenessScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Lot = cls.env["stock.lot"]
        cls.product_a, cls.product_b = cls.env["product.product"].create(
            [
                {"name": "PA", "is_storable": True, "tracking": "lot"},
                {"name": "PB", "is_storable": True, "tracking": "lot"},
            ]
        )

    def test_a_violation_on_a_cross_pair_is_not_this_batch_s(self):
        lot_a = self.Lot.create({"name": "N1", "product_id": self.product_a.id})
        lot_b = self.Lot.create({"name": "N2", "product_id": self.product_b.id})
        self.env.flush_all()
        self.env.cr.execute(
            """INSERT INTO stock_lot
               (name, product_id, company_id, active, create_uid, write_uid, create_date, write_date)
               VALUES ('N1', %s, NULL, true, 1, 1, now(), now()),
                      ('N1', %s, %s,   true, 1, 1, now(), now())""",
            (self.product_b.id, self.product_b.id, self.env.company.id),
        )
        self.env.invalidate_all()
        (lot_a + lot_b)._check_unique_lot()

    def test_a_real_duplicate_in_the_batch_is_still_reported(self):
        lot = self.Lot.create({"name": "M1", "product_id": self.product_a.id})
        self.env.flush_all()
        with self.assertRaises(ValidationError):
            self.Lot.create({"name": "M1", "product_id": self.product_a.id})
        self.assertTrue(lot.exists())

    def test_a_lot_can_be_duplicated_more_than_once(self):
        source = self.Lot.create({"name": "ORIG", "product_id": self.product_a.id})
        self.env.flush_all()
        first = source.copy()
        second = source.copy()
        self.env.flush_all()
        self.assertNotEqual(first.name, second.name)


class TestLotCompanyAtBranchDepth(TransactionCase):
    def test_the_owner_s_branch_gets_the_lot_at_any_depth(self):
        Company = self.env["res.company"]
        root = self.env.company
        chain = [root]
        for index in range(3):
            chain.append(
                Company.create({"name": "Branch %d" % index, "parent_id": chain[-1].id})
            )
        product = self.env["product.product"].create(
            {
                "name": "Root owned",
                "is_storable": True,
                "tracking": "serial",
                "company_id": root.id,
            }
        )
        for depth, company in enumerate(chain[1:], start=1):
            with self.subTest(depth=depth):
                lot = (
                    self.env["stock.lot"]
                    .with_company(company)
                    .with_context(allowed_company_ids=company.ids)
                    .new({"product_id": product.id})
                )
                lot._compute_company_id()
                self.assertEqual(
                    lot.company_id,
                    company,
                    "a branch that cannot reach the owner keeps its own company",
                )

    def test_an_accessible_owner_still_wins(self):
        product = self.env["product.product"].create(
            {
                "name": "Own company",
                "is_storable": True,
                "tracking": "serial",
                "company_id": self.env.company.id,
            }
        )
        lot = self.env["stock.lot"].create({"product_id": product.id})
        self.assertEqual(lot.company_id, self.env.company)

    def test_a_shared_product_makes_a_company_less_lot(self):
        product = self.env["product.product"].create(
            {"name": "Shared", "is_storable": True, "tracking": "serial"}
        )
        lot = self.env["stock.lot"].create({"product_id": product.id})
        self.assertFalse(lot.company_id)


class TestLotQuantityScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock = cls.env.ref("stock.stock_location_stock")
        cls.shelf = cls.env["stock.location"].create(
            {"name": "Shelf", "usage": "internal", "location_id": cls.stock.id}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Scoped", "is_storable": True, "tracking": "lot"}
        )
        cls.lot = cls.env["stock.lot"].create(
            {"name": "SCOPE", "product_id": cls.product.id}
        )
        cls.quant = cls.env["stock.quant"].create(
            {
                "product_id": cls.product.id,
                "location_id": cls.shelf.id,
                "quantity": 12.0,
                "lot_id": cls.lot.id,
            }
        )

    def test_strict_is_a_dependency_of_product_qty(self):
        scoped = {"location": self.stock.id}
        loose = self.lot.with_context(**scoped).product_qty
        strict = self.lot.with_context(strict=True, **scoped).product_qty
        self.assertEqual(loose, 12.0)
        self.assertEqual(strict, 0.0, "the quant is in a child of the scope")

    def test_moving_a_quant_moves_the_lot_s_single_location(self):
        self.assertEqual(self.lot.location_id, self.shelf)
        other = self.env["stock.location"].create(
            {"name": "Other", "usage": "internal", "location_id": self.stock.id}
        )
        self.quant.location_id = other
        self.env.flush_all()
        self.assertEqual(self.lot.location_id, other)

    def test_the_quantity_search_answers_the_operators_product_does(self):
        self.assertIn(
            self.lot,
            self.env["stock.lot"].search([("product_qty", "ilike", "12")]),
        )


class TestLotHookContracts(TransactionCase):
    def test_the_outgoing_domain_is_a_domain(self):
        self.assertIsInstance(
            self.env["stock.lot"]._get_domain_outgoing_move_lines(),
            Domain,
            "overrides combine it with | and callers with &",
        )

    def test_partners_from_deliveries_is_a_recordset(self):
        pickings = self.env["stock.picking"]
        self.assertEqual(
            self.env["stock.lot"]._get_partners_from_deliveries(pickings)._name,
            "res.partner",
        )

    def test_generate_lot_names_returns_names(self):
        names = self.env["stock.lot"].prepare_lot_names("SN0009", 3)
        self.assertEqual(names, ["SN0009", "SN0010", "SN0011"])

    def test_the_permission_hook_takes_its_products_as_an_argument(self):
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        picking_type.use_create_lots = False
        product = self.env["product.product"].create(
            {"name": "Blocked", "is_storable": True, "tracking": "lot"}
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.env.ref("stock.stock_location_stock").id,
            }
        )
        Lot = self.env["stock.lot"].with_context(active_picking_id=picking.id)
        with self.assertRaises(UserError):
            Lot.create({"name": "NOPE", "product_id": product.id})

    def test_renaming_a_lot_is_the_same_permission_as_naming_one(self):
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        product = self.env["product.product"].create(
            {"name": "Renamable", "is_storable": True, "tracking": "lot"}
        )
        lot = self.env["stock.lot"].create({"name": "KEEP", "product_id": product.id})
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.env.ref("stock.stock_location_stock").id,
            }
        )
        picking_type.use_create_lots = False
        with self.assertRaises(UserError):
            lot.with_context(active_picking_id=picking.id).write({"name": "RENAMED"})


class TestDisplayCompleteHasTwoInputs(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Displayable", "is_storable": True, "tracking": "lot"}
        )

    def test_a_saved_lot_is_complete_with_no_context(self):
        lot = self.env["stock.lot"].create({"product_id": self.product.id})
        self.assertTrue(lot.display_complete)

    def test_an_unsaved_lot_is_not_complete_by_default(self):
        lot = self.env["stock.lot"].new({"product_id": self.product.id})
        self.assertFalse(lot.display_complete)

    def test_the_context_key_completes_an_unsaved_lot(self):
        lot = (
            self.env["stock.lot"]
            .with_context(display_complete=True)
            .new({"product_id": self.product.id})
        )
        self.assertTrue(lot.display_complete)

    def test_the_key_is_a_declared_dependency(self):
        Lot = self.env["stock.lot"]
        __, depends_context = Lot._fields["display_complete"].get_depends(Lot)
        self.assertIn("display_complete", depends_context)

    def test_strict_is_a_declared_dependency_of_product_qty(self):
        Lot = self.env["stock.lot"]
        __, depends_context = Lot._fields["product_qty"].get_depends(Lot)
        self.assertIn("strict", depends_context)

    def test_the_value_is_a_boolean(self):
        lot = self.env["stock.lot"].create({"product_id": self.product.id})
        self.assertIs(lot.display_complete, True)
