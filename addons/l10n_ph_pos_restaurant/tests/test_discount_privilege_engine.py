# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegeEngine(TestPhCommon):
    """
    Coverage of pos.order._l10n_ph_apply_discount_privileges: the headcount
    pro-rating / quantity-splitting engine behind the (future) POS wizard.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("point_of_sale.group_pos_manager")

        ChartTemplate = cls.env["account.chart.template"].with_company(
            cls.company_data["company"],
        )
        cls.tax_sale_12 = ChartTemplate.ref("l10n_ph_tax_sale_12")
        cls.tax_sale_0_exempt_sc_pwd = ChartTemplate.ref("l10n_ph_tax_sale_0_exempt_sc_pwd")
        cls.fpos_sc_pwd = ChartTemplate.ref("l10n_ph_fiscal_position_discount_privileges")

        cls.discount_account = cls.company_data["default_account_revenue"].copy(
            {"name": "Discount Privilege Account"},
        )
        cls.privilege_sc = cls.env["l10n_ph.discount.privilege"].sudo().create(
            {
                "name": "Senior Citizen",
                "discount_type": "sc",
                "discount_amount": 0.2,
                "fiscal_position_id": cls.fpos_sc_pwd.id,
                "account_id": cls.discount_account.id,
            },
        )
        cls.privilege_pwd = cls.env["l10n_ph.discount.privilege"].sudo().create(
            {
                "name": "PWD",
                "discount_type": "pwd",
                "discount_amount": 0.2,
                "fiscal_position_id": cls.fpos_sc_pwd.id,
                "account_id": cls.discount_account.id,
            },
        )
        cls.pizza = cls.env["product.product"].create(
            {
                "name": "Pizza Margherita",
                "list_price": 1000.0,
                "taxes_id": [Command.set(cls.tax_sale_12.ids)],
                "property_account_income_id": cls.company_data["default_account_revenue"].id,
            },
        )
        cls.soda = cls.env["product.product"].create(
            {
                "name": "Coca-Cola",
                "list_price": 100.0,
                "taxes_id": [Command.set(cls.tax_sale_12.ids)],
                "property_account_income_id": cls.company_data["default_account_revenue"].id,
            },
        )
        cls.pos_config = cls.env["pos.config"].create(
            {"name": "Test Restaurant", "company_id": cls.company_data["company"].id},
        )
        cls.pos_session = cls.env["pos.session"].create(
            {"config_id": cls.pos_config.id, "user_id": cls.env.uid},
        )

    def _create_order(self, order_lines):
        """``order_lines``: list of (product, qty) pairs."""
        order = self.env["pos.order"].create(
            {
                "name": "Test Order",
                "company_id": self.company_data["company"].id,
                "session_id": self.pos_session.id,
                "amount_tax": 0.0,
                "amount_total": 0.0,
                "amount_paid": 0.0,
                "amount_return": 0.0,
                "lines": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "qty": qty,
                            "price_unit": product.list_price,
                            "tax_ids": [Command.set(self.tax_sale_12.ids)],
                            "price_subtotal": 0.0,
                            "price_subtotal_incl": 0.0,
                        },
                    )
                    for product, qty in order_lines
                ],
            },
        )
        # Standard POS helper: computes price_subtotal(_incl) from
        # price_unit/discount/tax_ids/qty instead of re-deriving the tax
        # math by hand here.
        order.lines._onchange_amount_line_all()
        return order

    def _holder_vals(self, privilege, name="ID Holder", id_number="123-456-789"):
        return {
            "privilege_id": privilege.id,
            "name": name,
            "id_number": id_number,
        }

    # ============================================================
    #  Whole-order split (no target line)
    # ============================================================

    def test_whole_order_split_conserves_quantity(self):
        """3 regular + 1 SC + 1 PWD sharing every line: quantities across the
        regular share and both holder shares must sum back to the original."""
        order = self._create_order([(self.pizza, 2.0), (self.soda, 4.0)])
        pizza_line, soda_line = order.lines.sorted("id")

        holders = order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz", "PWD-1"),
            ],
            num_persons_sharing=5,
        )
        self.assertEqual(len(holders), 2)
        self.assertEqual(order.l10n_ph_discount_privilege_holder_ids, holders)

        for original_line, original_qty in ((pizza_line, 2.0), (soda_line, 4.0)):
            siblings = order.lines.filtered(
                lambda line, p=original_line.product_id: line.product_id == p,
            )
            self.assertEqual(len(siblings), 3, "regular + SC + PWD shares")
            self.assertAlmostEqual(sum(siblings.mapped("qty")), original_qty, places=6)

            regular = siblings.filtered(lambda line: not line.l10n_ph_discount_privilege_id)
            sc_line = siblings.filtered(lambda line: line.l10n_ph_discount_privilege_id == self.privilege_sc)
            pwd_line = siblings.filtered(lambda line: line.l10n_ph_discount_privilege_id == self.privilege_pwd)
            per_person_qty = original_qty / 5

            # Regular share is untouched: same tax, no discount.
            self.assertRecordValues(regular, [{
                "qty": per_person_qty * 3,
                "tax_ids": self.tax_sale_12.ids,
                "discount": 0.0,
            }])

            # Each holder share: VAT-exempt tax swap + statutory 20% discount,
            # computed by the already-proven mixin on the split quantity.
            for holder_line, holder_id in ((sc_line, "SC-1"), (pwd_line, "PWD-1")):
                self.assertRecordValues(holder_line, [{
                    "qty": per_person_qty,
                    "tax_ids": self.tax_sale_0_exempt_sc_pwd.ids,
                    "discount": 20.0,
                }])
                self.assertEqual(
                    holder_line.l10n_ph_discount_privilege_holder_id.id_number, holder_id,
                )
                expected_discount = holder_line.price_unit * per_person_qty * 0.2
                self.assertAlmostEqual(
                    holder_line.l10n_ph_special_discount_amount, expected_discount, places=2,
                )

    def test_all_holders_no_regular_share_reuses_original_line(self):
        """When every diner is an ID holder, the original line is reused for
        the first holder instead of being shrunk to zero and orphaned."""
        order = self._create_order([(self.pizza, 2.0)])
        original_line = order.lines
        original_line_id = original_line.id

        holders = order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz"),
            ],
            num_persons_sharing=2,
        )
        self.assertEqual(len(order.lines), 2)
        self.assertIn(original_line_id, order.lines.ids)
        self.assertAlmostEqual(sum(order.lines.mapped("qty")), 2.0, places=6)
        self.assertEqual(order.lines.l10n_ph_discount_privilege_id, holders.privilege_id)

    def test_solo_diner_single_holder(self):
        order = self._create_order([(self.pizza, 1.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz")],
            num_persons_sharing=1,
        )
        self.assertEqual(len(order.lines), 1)
        self.assertRecordValues(order.lines, [{
            "l10n_ph_discount_privilege_id": self.privilege_sc.id,
            "qty": 1.0,
            "tax_ids": self.tax_sale_0_exempt_sc_pwd.ids,
            "l10n_ph_original_tax_ids": self.tax_sale_12.ids,
            "l10n_ph_special_discount_amount": 200.0,
            "l10n_ph_regular_discount_amount": 0.0,
        }])

    def test_holder_share_preserves_pre_existing_discount(self):
        """A manual discount already on the line before applying a privilege
        must be preserved as l10n_ph_original_discount, not silently dropped."""
        order = self._create_order([(self.pizza, 1.0)])
        order.lines.discount = 10.0
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz")],
            num_persons_sharing=1,
        )
        self.assertRecordValues(order.lines, [{
            "discount": 20.0,
            "l10n_ph_original_discount": 10.0,
        }])

    # ============================================================
    #  Single-line target (spec: "one product selected")
    # ============================================================

    def test_target_line_only_splits_that_line(self):
        order = self._create_order([(self.pizza, 2.0), (self.soda, 4.0)])
        pizza_line, soda_line = order.lines.sorted("id")

        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz")],
            num_persons_sharing=1,
            target_line=pizza_line,
        )

        # The untouched line is bit-for-bit unaffected.
        self.assertRecordValues(soda_line, [{
            "l10n_ph_discount_privilege_id": False,
            "qty": 4.0,
        }])

        pizza_lines = order.lines.filtered(lambda line: line.product_id == self.pizza)
        self.assertEqual(len(pizza_lines), 1)
        self.assertRecordValues(pizza_lines, [{
            "l10n_ph_discount_privilege_id": self.privilege_sc.id,
            "qty": 2.0,
        }])

    def test_composability_specific_item_then_whole_order(self):
        """Case 2 (exclusive item) followed by case 1 (shared remainder) on
        the same order: the already-privileged line must be excluded from
        the second, whole-order application."""
        order = self._create_order([(self.pizza, 2.0), (self.soda, 4.0)])
        pizza_line = order.lines.filtered(lambda line: line.product_id == self.pizza)

        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
            num_persons_sharing=1,
            target_line=pizza_line,
        )
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz", "PWD-1")],
            num_persons_sharing=5,
        )

        soda_lines = order.lines.filtered(lambda line: line.product_id == self.soda)
        self.assertEqual(len(soda_lines), 2, "regular + PWD share of the soda only")
        self.assertAlmostEqual(sum(soda_lines.mapped("qty")), 4.0, places=6)
        pizza_lines = order.lines.filtered(lambda line: line.product_id == self.pizza)
        self.assertEqual(len(pizza_lines), 1, "the pizza was already fully attributed to SC")
        self.assertEqual(pizza_lines.l10n_ph_discount_privilege_id, self.privilege_sc)

    # ============================================================
    #  extra_tax_data / subtotal refresh (POS does not auto-compute these
    #  from price_unit/discount/tax_ids/qty, unlike account.move.line, so
    #  the splitting engine must refresh them on every mutated line or the
    #  frontend's tax-display code crashes reading stale data)
    # ============================================================

    def test_split_lines_refresh_stored_amounts(self):
        """POS does not auto-compute price_subtotal(_incl)/extra_tax_data
        from price_unit/discount/tax_ids/qty: the splitting engine must
        refresh both on every mutated line, or the frontend's tax-display
        code crashes reading stale data."""
        order = self._create_order([(self.pizza, 5.0)])
        original_subtotal = order.lines.price_subtotal
        original_subtotal_incl = order.lines.price_subtotal_incl

        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz"),
            ],
            num_persons_sharing=5,
        )
        # The regular share is a plain qty resize: its subtotal must still be
        # an exact 3/5 slice of the original (undiscounted) line.
        regular = order.lines.filtered(lambda line: not line.l10n_ph_discount_privilege_id)
        self.assertAlmostEqual(regular.price_subtotal, original_subtotal * 3 / 5, places=2)
        self.assertAlmostEqual(regular.price_subtotal_incl, original_subtotal_incl * 3 / 5, places=2)

        # extra_tax_data must be recomputed too, for every share alike.
        for line in order.lines:
            expected = self.env["account.tax"]._export_base_line_extra_tax_data(
                line._l10n_ph_prepare_taxed_base_line(),
            )
            # fields.Json stores/reads an empty dict back as False.
            self.assertEqual(line.extra_tax_data, expected or False)

    # ============================================================
    #  RPC entry point (l10n_ph_apply_discount_privileges)
    # ============================================================

    def test_rpc_entry_point_returns_pos_load_shaped_data(self):
        """The public RPC wrapper must return data in the same
        {model: [record dicts]} shape the frontend already knows how to
        merge into its local store for any other server-driven mutation."""
        order = self._create_order([(self.pizza, 2.0)])
        line = order.lines
        result = order.l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
            num_persons_sharing=2,
            target_line_uuid=line.uuid,
        )
        self.assertEqual(set(result.keys()), {"pos.order", "pos.order.line", "l10n_ph.pos.discount.privilege.holder"})
        self.assertEqual(len(result["pos.order"]), 1)
        self.assertEqual(result["pos.order"][0]["id"], order.id)
        self.assertEqual(len(result["pos.order.line"]), 2, "regular + SC share")
        self.assertEqual(len(result["l10n_ph.pos.discount.privilege.holder"]), 1)
        self.assertEqual(result["l10n_ph.pos.discount.privilege.holder"][0]["id_number"], "SC-1")

    def test_rpc_entry_point_resolves_target_line_by_uuid(self):
        order = self._create_order([(self.pizza, 2.0), (self.soda, 4.0)])
        pizza_line = order.lines.filtered(lambda line: line.product_id == self.pizza)
        soda_line = order.lines.filtered(lambda line: line.product_id == self.soda)

        order.l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz")],
            num_persons_sharing=1,
            target_line_uuid=pizza_line.uuid,
        )
        self.assertFalse(soda_line.l10n_ph_discount_privilege_id)
        self.assertEqual(
            order.lines.filtered(lambda line: line.product_id == self.pizza).l10n_ph_discount_privilege_id,
            self.privilege_sc,
        )

    # ============================================================
    #  Validation
    # ============================================================

    def test_requires_at_least_one_holder(self):
        order = self._create_order([(self.pizza, 1.0)])
        with self.assertRaises(UserError):
            order._l10n_ph_apply_discount_privileges(holders_vals=[], num_persons_sharing=1)

    def test_persons_sharing_must_cover_all_holders(self):
        order = self._create_order([(self.pizza, 1.0)])
        with self.assertRaises(UserError):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[
                    self._holder_vals(self.privilege_sc),
                    self._holder_vals(self.privilege_pwd),
                ],
                num_persons_sharing=1,
            )

    def test_target_line_from_another_order_rejected(self):
        order_a = self._create_order([(self.pizza, 1.0)])
        order_b = self._create_order([(self.soda, 1.0)])
        with self.assertRaises(UserError):
            order_a._l10n_ph_apply_discount_privileges(
                holders_vals=[self._holder_vals(self.privilege_sc)],
                num_persons_sharing=1,
                target_line=order_b.lines,
            )

    def test_target_line_already_privileged_rejected(self):
        order = self._create_order([(self.pizza, 1.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=1,
            target_line=order.lines,
        )
        with self.assertRaises(UserError):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[self._holder_vals(self.privilege_pwd)],
                num_persons_sharing=1,
                target_line=order.lines,
            )

    def test_no_eligible_lines_left_rejected(self):
        order = self._create_order([(self.pizza, 1.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=1,
        )
        with self.assertRaises(UserError):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[self._holder_vals(self.privilege_pwd)],
                num_persons_sharing=1,
            )
