# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import count

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon
from odoo.addons.l10n_ph_invoice.models.l10n_ph_discount_privilege import (
    PARTNER_IDENTIFIER_KEYS,
)


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

        cls.privilege_sc = ChartTemplate.ref("l10n_ph_discount_privilege_sc_20_vat_incl")
        cls.privilege_pwd = ChartTemplate.ref("l10n_ph_discount_privilege_pwd_20_vat_incl")
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

    _id_numbers = count(1)

    def setUp(self):
        super().setUp()
        self._holder_partners = {}

    def _holder_vals(self, privilege, name=None, id_number=None):
        """
        Holder values for the contact named ``name`` (one contact per name,
        created as needed), whose ID of ``privilege``'s type is set to
        ``id_number`` (or kept, or generated when unset).
        """
        number = next(self._id_numbers)
        name = name or f"ID Holder {number}"
        partner = self._holder_partners.get(name) or self.env["res.partner"].create({"name": name})
        self._holder_partners[name] = partner
        identifiers = partner.additional_identifiers or {}
        key = PARTNER_IDENTIFIER_KEYS[privilege.discount_type]
        partner.additional_identifiers = {**identifiers, key: id_number or identifiers.get(key) or f"ID-{number}"}
        return {"privilege_id": privilege.id, "partner_id": partner.id}

    # ============================================================
    #  Whole-order split (no target line)
    # ============================================================

    def test_whole_order_split_conserves_quantity(self):
        """3 regular + 1 SC + 1 PWD sharing every line: quantities across the
        regular share and both holder shares must sum back to the original."""
        order = self._create_order([(self.pizza, 2.0), (self.soda, 4.0)])
        pizza_line, soda_line = order.lines.sorted("id")

        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz", "PWD-1"),
            ],
            num_persons_sharing=5,
        )

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
            for holder_line, name, id_number in (
                (sc_line, "Juan Dela Cruz", "SC-1"),
                (pwd_line, "Abigail Dela Cruz", "PWD-1"),
            ):
                self.assertRecordValues(holder_line, [{
                    "qty": per_person_qty,
                    "tax_ids": self.tax_sale_0_exempt_sc_pwd.ids,
                    "discount": 20.0,
                    "l10n_ph_holder_name": name,
                    "l10n_ph_holder_id_number": id_number,
                }])
                expected_discount = holder_line.price_unit * per_person_qty * 0.2
                self.assertAlmostEqual(
                    holder_line.l10n_ph_special_discount_amount, expected_discount, places=2,
                )

    def test_all_holders_no_regular_share_reuses_original_line(self):
        """When every diner is an ID holder, the original line is reused for
        the first holder instead of being shrunk to zero and orphaned, and
        the other holders' shares still record the pre-privilege values."""
        order = self._create_order([(self.pizza, 2.0)])
        original_line = order.lines
        original_line_id = original_line.id
        original_line.discount = 10.0
        original_line._onchange_amount_line_all()

        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz"),
            ],
            num_persons_sharing=2,
        )
        self.assertEqual(len(order.lines), 2)
        self.assertIn(original_line_id, order.lines.ids)
        self.assertAlmostEqual(sum(order.lines.mapped("qty")), 2.0, places=6)
        self.assertEqual(order.lines.l10n_ph_discount_privilege_id, self.privilege_sc | self.privilege_pwd)
        self.assertRecordValues(order.lines.sorted("id"), [
            {
                "discount": 20.0,
                "price_unit": 1000.0,
                "tax_ids": self.tax_sale_0_exempt_sc_pwd.ids,
                "l10n_ph_original_discount": 10.0,
                "l10n_ph_original_price_unit": 1000.0,
                "l10n_ph_original_tax_ids": self.tax_sale_12.ids,
                # Not repriced by the POS from the pricelist.
                "price_type": "manual",
            },
        ] * 2)

    def test_split_conserves_quantity_with_rounding(self):
        """Quantities are stored with the "Product Unit" precision: rounding
        each share on its own must never add or lose quantity."""
        for qty, num_persons, privileges in (
            (2.0, 3, [self.privilege_sc, self.privilege_pwd]),  # 0.67 x 3 would be 2.01
            (1.0, 3, [self.privilege_sc, self.privilege_pwd, self.privilege_sc]),  # 0.33 x 3 would be 0.99
        ):
            with self.subTest(qty=qty, num_persons=num_persons, num_holders=len(privileges)):
                order = self._create_order([(self.pizza, qty)])
                order._l10n_ph_apply_discount_privileges(
                    holders_vals=[self._holder_vals(privilege) for privilege in privileges],
                    num_persons_sharing=num_persons,
                )
                self.assertEqual(len(order.lines), num_persons)
                self.assertAlmostEqual(sum(order.lines.mapped("qty")), qty, places=6)

    def test_split_into_empty_shares_rejected(self):
        """A quantity too small to give everyone a share at the "Product
        Unit" precision can't be split: an ID holder's share would be empty."""
        order = self._create_order([(self.pizza, 0.5)])
        with self.assertRaises(UserError):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[self._holder_vals(self.privilege_sc)],
                num_persons_sharing=100,
            )

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
        """Spec section 4 "Specific Items": a line ordered exclusively for the ID
        holder is fully attributed to them (num_persons_sharing=1 for that
        line's own invocation); the rest of the order is untouched."""
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

    def test_target_line_pro_rates_by_real_headcount(self):
        """Spec section 8.2 "Group Orders, one product selected": selecting a line
        still pro-rates it by the table's actual headcount ("the only
        difference is that the only selected item has the 0% Exempt
        SC/PWD"). Unlike the "Specific Items" case above, the rest of the
        order is untouched but the selected line itself still gets a
        regular share alongside the holder shares."""
        order = self._create_order([(self.pizza, 5.0), (self.soda, 4.0)])
        pizza_line, soda_line = order.lines.sorted("id")

        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz"),
            ],
            num_persons_sharing=5,
            target_line=pizza_line,
        )

        self.assertRecordValues(soda_line, [{
            "l10n_ph_discount_privilege_id": False,
            "qty": 4.0,
        }])
        pizza_lines = order.lines.filtered(lambda line: line.product_id == self.pizza)
        self.assertEqual(len(pizza_lines), 3, "regular + SC + PWD shares of the selected line only")
        self.assertAlmostEqual(sum(pizza_lines.mapped("qty")), 5.0, places=6)
        regular = pizza_lines.filtered(lambda line: not line.l10n_ph_discount_privilege_id)
        self.assertAlmostEqual(regular.qty, 3.0, places=6)

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
        holder_vals = self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")
        result = order.l10n_ph_apply_discount_privileges(
            holders_vals=[holder_vals],
            num_persons_sharing=2,
            target_line_uuid=line.uuid,
        )
        self.assertEqual(set(result.keys()), {
            "pos.order", "pos.order.line", "pos.prep.line", "res.partner", "product.attribute.custom.value",
        })
        self.assertEqual(len(result["pos.order"]), 1)
        self.assertEqual(result["pos.order"][0]["id"], order.id)
        self.assertEqual(len(result["pos.order.line"]), 2, "regular + SC share")
        self.assertEqual(
            {line_vals["l10n_ph_holder_id_number"] for line_vals in result["pos.order.line"]},
            {"SC-1", False},
        )
        self.assertEqual([partner_vals["id"] for partner_vals in result["res.partner"]], [holder_vals["partner_id"]])

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

    def test_paid_order_rejected(self):
        order = self._create_order([(self.pizza, 1.0)])
        order.state = "paid"
        with self.assertRaises(UserError):
            order.l10n_ph_apply_discount_privileges(
                holders_vals=[self._holder_vals(self.privilege_sc)],
                num_persons_sharing=1,
            )
        self.assertFalse(order.lines.l10n_ph_discount_privilege_id)

    def test_rpc_entry_point_unknown_target_line_rejected(self):
        """An unknown line uuid must not fall back on privileging the whole
        order."""
        order = self._create_order([(self.pizza, 2.0), (self.soda, 4.0)])
        with self.assertRaises(UserError):
            order.l10n_ph_apply_discount_privileges(
                holders_vals=[self._holder_vals(self.privilege_sc)],
                num_persons_sharing=1,
                target_line_uuid="not-a-line-of-this-order",
            )
        self.assertFalse(order.lines.l10n_ph_discount_privilege_id)

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

    def test_rpc_entry_point_ignores_unknown_holder_fields(self):
        order = self._create_order([(self.pizza, 1.0)])
        other_order = self._create_order([(self.soda, 1.0)])
        order.l10n_ph_apply_discount_privileges(
            holders_vals=[{
                **self._holder_vals(self.privilege_sc),
                "order_id": other_order.id,
                "price_unit": 0.0,
                "name": "Somebody Else",
                "id_number": "INJECTED",
                "l10n_ph_holder_id_number": "INJECTED",
            }],
            num_persons_sharing=1,
        )
        self.assertRecordValues(order.lines, [{
            "l10n_ph_discount_privilege_id": self.privilege_sc.id,
            "price_unit": 1000.0,
        }])
        self.assertNotEqual(order.lines.l10n_ph_holder_id_number, "INJECTED")
        self.assertNotEqual(order.lines.l10n_ph_holder_name, "Somebody Else")
        self.assertEqual(other_order.lines.product_id, self.soda)
        self.assertFalse(other_order.lines.l10n_ph_discount_privilege_id)

    def test_holder_information_comes_from_contact(self):
        """An ID holder's name and ID number are taken from their contact,
        and recorded as presented at the time of sale: editing the contact
        later on doesn't alter them."""
        order = self._create_order([(self.pizza, 2.0)])
        holder_vals = self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=2)
        partner = self.env["res.partner"].browse(holder_vals["partner_id"])
        partner.write({"name": "Juan P. Dela Cruz", "additional_identifiers": {"PH_SC_ID": "SC-2"}})
        self.assertRecordValues(order.lines.sorted("id"), [
            {"l10n_ph_holder_partner_id": False, "l10n_ph_holder_name": False, "l10n_ph_holder_id_number": False},
            {
                "l10n_ph_holder_partner_id": partner.id,
                "l10n_ph_holder_name": "Juan Dela Cruz",
                "l10n_ph_holder_id_number": "SC-1",
            },
        ])

    def test_holder_contact_and_id_required(self):
        order = self._create_order([(self.pizza, 1.0)])
        without_id = self.env["res.partner"].create({"name": "Juan Dela Cruz"})
        pwd_id_only = self.env["res.partner"].create({
            "name": "Abigail Dela Cruz",
            "additional_identifiers": {"PH_PWD_ID": "PWD-1"},
        })
        for partner in (self.env["res.partner"], without_id, pwd_id_only):
            with self.subTest(partner=partner.name), self.assertRaises(UserError):
                order._l10n_ph_apply_discount_privileges(
                    holders_vals=[{"privilege_id": self.privilege_sc.id, "partner_id": partner.id}],
                    num_persons_sharing=1,
                )
        self.assertFalse(order.lines.l10n_ph_discount_privilege_id)

    def test_same_holder_twice_rejected(self):
        order = self._create_order([(self.pizza, 2.0)])
        with self.assertRaises(UserError):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[
                    self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1"),
                    self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1"),
                ],
                num_persons_sharing=2,
            )

    def test_one_privilege_per_person(self):
        """SC/PWD privileges can't be combined: a person (identified by their
        contact, or their name) presents a single ID per order."""
        for case, first_holders, second_holders in (
            ("twice in the same application", [], [
                (self.privilege_sc, "Juan Dela Cruz", "SC-1"),
                (self.privilege_pwd, "Juan Dela Cruz", "PWD-1"),
            ]),
            (
                "another privilege later on",
                [(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
                [(self.privilege_pwd, "Juan Dela Cruz", "PWD-1")],
            ),
            (
                "the same privilege with another ID",
                [(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
                [(self.privilege_sc, "Juan Dela Cruz", "SC-2")],
            ),
            (
                "somebody else's ID",
                [(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
                [(self.privilege_sc, "Maria Dela Cruz", "SC-1")],
            ),
        ):
            with self.subTest(case=case):
                self._holder_partners = {}
                order = self._create_order([(self.pizza, 2.0), (self.soda, 2.0)])
                if first_holders:
                    order._l10n_ph_apply_discount_privileges(
                        holders_vals=[self._holder_vals(*holder) for holder in first_holders],
                        num_persons_sharing=2,
                        target_line=order.lines[0],
                    )
                # Created outside of assertRaises, which rolls back what happens in it.
                second_holders_vals = [self._holder_vals(*holder) for holder in second_holders]
                with self.assertRaises(UserError):
                    order._l10n_ph_apply_discount_privileges(
                        holders_vals=second_holders_vals,
                        num_persons_sharing=2,
                    )

    def test_same_holder_can_be_given_more_shares(self):
        """An ID holder already on the order can be given shares of other
        items with the same privilege and ID."""
        order = self._create_order([(self.pizza, 2.0), (self.soda, 2.0)])
        holder_vals = self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[holder_vals], num_persons_sharing=2, target_line=order.lines[0],
        )
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=2)
        self.assertEqual(
            set(order.lines.filtered("l10n_ph_discount_privilege_id").mapped("l10n_ph_holder_id_number")),
            {"SC-1"},
        )

    def test_privileged_line_cannot_be_discounted_again(self):
        """No double discounting: a privileged share's discount is its
        privilege's, whatever the POS sends."""
        order = self._create_order([(self.pizza, 1.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=1,
        )
        with self.assertRaises(ValidationError):
            order.lines.discount = 30.0

    def test_non_goods_lines_are_not_split(self):
        """Global discounts, rewards and tips aren't goods sold to the ID
        holder: they are never split nor privileged."""
        order = self._create_order([(self.pizza, 2.0), (self.soda, 1.0)])
        tip_product = self.env["product.product"].create({"name": "Tip", "list_price": 50.0})
        self.pos_config.tip_product_id = tip_product
        discount_line, tip_line = self.env["pos.order.line"].create([
            {
                "order_id": order.id,
                "product_id": self.soda.id,
                "qty": 1.0,
                "price_unit": -100.0,
                "price_subtotal": -100.0,
                "price_subtotal_incl": -100.0,
            },
            {
                "order_id": order.id,
                "product_id": tip_product.id,
                "qty": 1.0,
                "price_unit": 50.0,
                "price_subtotal": 50.0,
                "price_subtotal_incl": 50.0,
            },
        ])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=2,
        )
        self.assertFalse((discount_line | tip_line).l10n_ph_discount_privilege_id)
        self.assertRecordValues(discount_line | tip_line, [{"qty": 1.0}, {"qty": 1.0}])
        self.assertEqual(len(order.lines), 6, "pizza and soda split in 2 shares each")
        with self.assertRaises(UserError):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[self._holder_vals(self.privilege_pwd)],
                num_persons_sharing=1,
                target_line=tip_line,
            )

    def test_persons_sharing_must_be_whole_number(self):
        order = self._create_order([(self.pizza, 1.0)])
        for num_persons_sharing in (True, 2.5, "2"):
            with self.subTest(num_persons_sharing=num_persons_sharing), self.assertRaises(UserError):
                order._l10n_ph_apply_discount_privileges(
                    holders_vals=[self._holder_vals(self.privilege_sc)],
                    num_persons_sharing=num_persons_sharing,
                )

    def test_representative_required_when_holder_absent(self):
        order = self._create_order([(self.pizza, 1.0)])
        # Created outside of assertRaises, which rolls back what happens in it.
        holder_vals = self._holder_vals(self.privilege_sc, "Juan Dela Cruz")
        with self.assertRaises(UserError):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[{**holder_vals, "representative_name": "Maria Dela Cruz"}],
                num_persons_sharing=1,
            )
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[{
                **holder_vals,
                "representative_name": "Maria Dela Cruz",
                "representative_id": "REP-1",
            }],
            num_persons_sharing=1,
        )
        self.assertRecordValues(order.lines, [{
            "l10n_ph_holder_representative_name": "Maria Dela Cruz",
            "l10n_ph_holder_representative_id": "REP-1",
        }])

    def test_resplit_keeps_remaining_regular_headcount(self):
        """An ID presented later on (e.g. a forgotten PWD ID) is pro-rated
        among the regular persons still sharing the order, not the whole
        table again: 5 persons, SC applied first, then PWD."""
        order = self._create_order([(self.pizza, 5.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz")],
            num_persons_sharing=5,
        )
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz")],
            num_persons_sharing=5,
        )
        qty_per_privilege = {
            line.l10n_ph_discount_privilege_id: line.qty for line in order.lines
        }
        self.assertEqual(qty_per_privilege, {
            self.env["l10n_ph.discount.privilege"]: 3.0,
            self.privilege_sc: 1.0,
            self.privilege_pwd: 1.0,
        })
        regular = order.lines.filtered(lambda line: not line.l10n_ph_discount_privilege_id)
        self.assertEqual(regular.l10n_ph_persons_sharing, 3)

    def test_split_updates_order_totals(self):
        order = self._create_order([(self.pizza, 5.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=5,
        )
        # 4 regular shares at 1,120 VAT included + 1 SC share at 1,000 - 20%.
        self.assertAlmostEqual(order.amount_total, 4 * 1120.0 + 800.0, places=2)
        self.assertAlmostEqual(order.amount_tax, 4 * 120.0, places=2)

    def test_split_is_not_an_order_edit(self):
        """Moving quantity to the ID holder shares is not a cancellation:
        the order must not be flagged as edited, and its chatter gets one
        summary of the privileges applied instead of quantity changes."""
        order = self._create_order([(self.pizza, 3.0)])
        messages_before = order.message_ids
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
            num_persons_sharing=3,
        )
        self.assertFalse(any(order.lines.mapped("is_edited")))
        self.assertFalse(order.is_edited)
        new_messages = order.message_ids - messages_before
        self.assertEqual(len(new_messages), 1)
        self.assertIn("Juan Dela Cruz", new_messages.body)
        self.assertIn("SC-1", new_messages.body)

    def test_split_context_key_not_honored_from_user_calls(self):
        """The key keeping a split from being logged as an edit must not let a
        user hide quantity decreases or other messages from the order."""
        order = self._create_order([(self.pizza, 3.0)])
        order_as_user = order.with_context(l10n_ph_discount_privilege_split=True)
        messages_before = order.message_ids
        order_as_user.lines.write({"qty": 1.0})
        order_as_user.message_post(body="Payment method changed")
        self.assertTrue(order.lines.is_edited)
        self.assertEqual(len(order.message_ids - messages_before), 2)

    # ============================================================
    #  Preparation (kitchen) quantities
    # ============================================================

    def _send_to_preparation(self, line, quantity, cancelled=0.0):
        prep_order = self.env["pos.prep.order"].create({"pos_order_id": line.order_id.id})
        self.env["pos.prep.line"].create({
            "prep_order_id": prep_order.id,
            "pos_order_line_id": line.id,
            "product_id": line.product_id.id,
            "quantity": quantity,
            "cancelled": cancelled,
        })

    def _get_sent_qty(self, line):
        return sum(prep_line.quantity - prep_line.cancelled for prep_line in line.prep_line_ids)

    def test_split_moves_sent_quantities_to_holder_shares(self):
        """Once sent to the kitchen, a split must not show up as cancelled and
        new items to prepare: the POS compares each line's quantity with its
        sent quantity strictly, so they must match exactly."""
        for qty, sent, cancelled, num_persons, privileges in (
            (1.0, 1.0, 0.0, 3, [self.privilege_sc, self.privilege_pwd, self.privilege_sc]),
            (3.0, 4.0, 1.0, 3, [self.privilege_sc]),
        ):
            with self.subTest(qty=qty, sent=sent, cancelled=cancelled):
                order = self._create_order([(self.pizza, qty)])
                self._send_to_preparation(order.lines, sent, cancelled)
                order._l10n_ph_apply_discount_privileges(
                    holders_vals=[self._holder_vals(privilege) for privilege in privileges],
                    num_persons_sharing=num_persons,
                )
                for line in order.lines:
                    self.assertEqual(self._get_sent_qty(line), line.qty)

    def test_split_partially_sent_line(self):
        """Quantity not sent yet stays on as few lines as possible: the sent
        quantity goes to the ID holder shares first."""
        order = self._create_order([(self.pizza, 3.0)])
        self._send_to_preparation(order.lines, 2.0)
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=3,
        )
        regular = order.lines.filtered(lambda line: not line.l10n_ph_discount_privilege_id)
        holder_line = order.lines - regular
        self.assertEqual(self._get_sent_qty(holder_line), holder_line.qty)
        self.assertEqual(self._get_sent_qty(regular), 1.0)
        self.assertEqual(regular.qty, 2.0)

    # ============================================================
    #  Refunds
    # ============================================================

    def test_refund_lines_keep_privilege(self):
        order = self._create_order([(self.pizza, 3.0)])
        holder_vals = self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=3)
        sc_line = order.lines.filtered("l10n_ph_discount_privilege_id")

        # As built by the POS frontend: every loaded field is sent, the
        # privilege ones being empty.
        refund_order = self._create_order([])
        refund_line = self.env["pos.order.line"].create({
            "order_id": refund_order.id,
            "product_id": self.pizza.id,
            "qty": -1.0,
            "price_unit": sc_line.price_unit,
            "discount": sc_line.discount,
            "tax_ids": [Command.set(sc_line.tax_ids.ids)],
            "refunded_orderline_id": sc_line.id,
            "price_subtotal": 0.0,
            "price_subtotal_incl": 0.0,
            "l10n_ph_discount_privilege_id": False,
            "l10n_ph_original_tax_ids": [],
        })
        self.assertRecordValues(refund_line, [{
            "l10n_ph_discount_privilege_id": self.privilege_sc.id,
            "l10n_ph_holder_partner_id": holder_vals["partner_id"],
            "l10n_ph_holder_name": "Juan Dela Cruz",
            "l10n_ph_holder_id_number": "SC-1",
            "l10n_ph_original_tax_ids": self.tax_sale_12.ids,
            "l10n_ph_original_discount": 0.0,
        }])

        # Through the backend refund, which copies the refunded lines.
        other_order = self._create_order([(self.pizza, 3.0)])
        other_order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz", "PWD-1")],
            num_persons_sharing=3,
        )
        other_order.state = "paid"
        backend_refund = other_order._refund()
        self.assertRecordValues(backend_refund.lines.filtered("l10n_ph_discount_privilege_id"), [{
            "l10n_ph_holder_name": "Abigail Dela Cruz",
            "l10n_ph_holder_id_number": "PWD-1",
        }])

    # ============================================================
    #  Privilege scope
    # ============================================================

    def test_privilege_only_applies_to_its_categories_and_taxes(self):
        """Like the invoice wizard, a privilege only covers the products of
        its categories, and the taxes its fiscal position exempts: the ID
        holder's share of anything else stays among the regular ones."""
        food = self.env["product.category"].create({"name": "Food"})
        self.pizza.categ_id = food
        privilege_sc = self.privilege_sc.copy({"name": "SC on food", "applied_to_category_ids": food.ids})
        order = self._create_order([(self.pizza, 2.0), (self.soda, 2.0), (self.pizza, 2.0)])
        pizza, soda, exempt_pizza = order.lines
        exempt_pizza.tax_ids = self.tax_sale_0_exempt_sc_pwd
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(privilege_sc, "Juan Dela Cruz"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz"),
            ],
            num_persons_sharing=4,
        )
        self.assertRecordValues(order.lines.sorted("id"), [
            {"product_id": self.pizza.id, "qty": 1.0, "l10n_ph_discount_privilege_id": False},
            # Only the PWD holder takes their share of the soda.
            {"product_id": self.soda.id, "qty": 1.5, "l10n_ph_discount_privilege_id": False},
            {"product_id": self.pizza.id, "qty": 2.0, "l10n_ph_discount_privilege_id": False},
            {"product_id": self.pizza.id, "qty": 0.5, "l10n_ph_discount_privilege_id": privilege_sc.id},
            {"product_id": self.pizza.id, "qty": 0.5, "l10n_ph_discount_privilege_id": self.privilege_pwd.id},
            {"product_id": self.soda.id, "qty": 0.5, "l10n_ph_discount_privilege_id": self.privilege_pwd.id},
        ])
        self.assertEqual((pizza | soda | exempt_pizza).mapped("l10n_ph_persons_sharing"), [2, 3, 0])

        with self.assertRaisesRegex(UserError, "does not apply to"):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[self._holder_vals(privilege_sc, "Juan Dela Cruz")],
                num_persons_sharing=2,
                target_line=soda,
            )

    def test_privilege_applying_to_no_line_rejected(self):
        order = self._create_order([(self.soda, 2.0)])
        order.lines.tax_ids = self.tax_sale_0_exempt_sc_pwd
        with self.assertRaisesRegex(UserError, "do not apply to any line"):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[self._holder_vals(self.privilege_sc)],
                num_persons_sharing=2,
            )

    def test_holder_not_given_another_share_of_the_same_line(self):
        """Re-applying an ID holder on the whole order (e.g. for dishes ordered
        later) must not give them another share of the regular share left by
        their earlier split: they aren't among its persons anymore."""
        order = self._create_order([(self.pizza, 4.0)])
        holder_vals = self._holder_vals(self.privilege_sc, "Juan Dela Cruz")
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=4)
        pizza = order.lines.filtered(lambda line: not line.l10n_ph_discount_privilege_id)
        soda = self.env["pos.order.line"].create({
            "order_id": order.id,
            "product_id": self.soda.id,
            "qty": 2.0,
            "price_unit": self.soda.list_price,
            "tax_ids": [Command.set(self.tax_sale_12.ids)],
            "price_subtotal": 0.0,
            "price_subtotal_incl": 0.0,
        })
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=2)
        self.assertRecordValues(pizza | soda, [
            {"qty": 3.0, "l10n_ph_persons_sharing": 3},
            {"qty": 1.0, "l10n_ph_persons_sharing": 1},
        ])
        holder_lines = order.lines.filtered("l10n_ph_discount_privilege_id")
        self.assertEqual(sorted(holder_lines.mapped("qty")), [1.0, 1.0])
        self.assertEqual(holder_lines.product_id, self.pizza | self.soda)

        with self.assertRaisesRegex(UserError, "already has their share"):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[holder_vals], num_persons_sharing=3, target_line=pizza,
            )

    # ============================================================
    #  Prices
    # ============================================================

    def test_price_included_by_company_setting(self):
        """The VAT is removed from the price of a holder share when the tax is
        included in price through the company's setting too, not only through
        the tax's own override."""
        self.company_data["company"].account_price_include = "tax_included"
        self.tax_sale_12.price_include_override = False
        self.assertTrue(self.tax_sale_12.price_include)
        order = self._create_order([(self.soda, 1.0)])
        self.assertAlmostEqual(order.lines.price_subtotal_incl, 100.0)
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=1,
        )
        self.assertAlmostEqual(order.lines.price_unit, 100.0 / 1.12)
        self.assertRecordValues(order.lines, [{
            "l10n_ph_original_price_unit": 100.0,
            "price_subtotal_incl": 71.43,
        }])

    def test_holder_shares_keep_custom_attribute_values(self):
        attribute = self.env["product.attribute"].create({
            "name": "Toppings",
            "create_variant": "no_variant",
            "value_ids": [Command.create({"name": "Custom", "is_custom": True})],
        })
        self.pizza.product_tmpl_id.attribute_line_ids = [Command.create({
            "attribute_id": attribute.id,
            "value_ids": attribute.value_ids.ids,
        })]
        custom_value = self.pizza.product_tmpl_id.attribute_line_ids.product_template_value_ids
        order = self._create_order([(self.pizza, 2.0)])
        order.lines.write({
            "attribute_value_ids": custom_value.ids,
            "custom_attribute_value_ids": [Command.create({
                "custom_product_template_attribute_value_id": custom_value.id,
                "custom_value": "No onions",
            })],
        })
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=2,
        )
        self.assertEqual(len(order.lines), 2)
        for line in order.lines:
            self.assertEqual(line.custom_attribute_value_ids.mapped("custom_value"), ["No onions"])
        self.assertEqual(len(set(order.lines.custom_attribute_value_ids.mapped("uuid"))), 2)

    # ============================================================
    #  Undo (l10n_ph_remove_discount_privilege)
    # ============================================================

    def test_remove_privilege_gives_share_back_to_regular_share(self):
        order = self._create_order([(self.pizza, 3.0)])
        self._send_to_preparation(order.lines, 3.0)
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz"),
            ],
            num_persons_sharing=3,
        )
        regular = order.lines.filtered(lambda line: not line.l10n_ph_discount_privilege_id)
        sc_line = order.lines.filtered(lambda line: line.l10n_ph_discount_privilege_id == self.privilege_sc)
        result = order.l10n_ph_remove_discount_privilege(sc_line.uuid)

        self.assertFalse(sc_line.exists())
        self.assertNotIn(sc_line.id, [line_vals["id"] for line_vals in result["pos.order.line"]])
        self.assertRecordValues(regular, [{
            "qty": 2.0,
            "l10n_ph_persons_sharing": 2,
            "price_subtotal": 2000.0,
        }])
        # Its quantity sent to the kitchen comes back with it.
        self.assertEqual(self._get_sent_qty(regular), 2.0)
        self.assertAlmostEqual(order.amount_total, 2000.0 * 1.12 + 800.0, places=2)
        self.assertIn("Discount privilege of Juan Dela Cruz removed", order.message_ids[0].body)

    def test_remove_privilege_without_regular_share(self):
        """With no regular share to give it back to, the share becomes a
        regular line of its own again, priced and taxed as before the split."""
        order = self._create_order([(self.pizza, 1.0)])
        order.lines.discount = 10.0
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=1,
        )
        order.l10n_ph_remove_discount_privilege(order.lines.uuid)
        self.assertRecordValues(order.lines, [{
            "qty": 1.0,
            "price_unit": 1000.0,
            "discount": 10.0,
            "tax_ids": self.tax_sale_12.ids,
            "l10n_ph_discount_privilege_id": False,
            "l10n_ph_holder_partner_id": False,
            "l10n_ph_holder_name": False,
            "l10n_ph_persons_sharing": 1,
            "price_subtotal": 900.0,
        }])

    def test_remove_privilege_from_regular_line_rejected(self):
        order = self._create_order([(self.pizza, 1.0)])
        with self.assertRaises(UserError):
            order.l10n_ph_remove_discount_privilege(order.lines.uuid)
