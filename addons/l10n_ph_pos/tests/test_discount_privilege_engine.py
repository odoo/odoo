# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_ph_pos.tests.common import TestPosDiscountPrivilegeCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegeEngine(TestPosDiscountPrivilegeCommon):
    """
    Coverage of pos.order._l10n_ph_apply_discount_privileges: the headcount
    pro-rating / quantity-splitting engine behind the POS Discount Privileges
    dialog. The ID holder rules, pricing and undo are in test_discount_privilege_line.
    """

    # ============================================================
    #  Whole-order split (no target line)
    # ============================================================

    def test_whole_order_split(self):
        """3 regular + 1 SC + 1 PWD sharing every line: the regular share is
        untouched, each holder share is VAT exempt and discounted 20%, and
        the quantities sum back to the original ones, and the order's totals follow."""
        order = self._create_order([(self.pizza, 2.0), (self.soda, 4.0)])

        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz", "PWD-1"),
            ],
            num_persons_sharing=5,
        )

        holder_vals = {
            "tax_ids": self.tax_sale_0_exempt_sc_pwd.ids,
            "discount": 20.0,
            "l10n_ph_persons_sharing": 0,
        }
        sc_vals = {
            **holder_vals,
            "l10n_ph_discount_privilege_id": self.privilege_sc.id,
            "l10n_ph_holder_name": "Juan Dela Cruz",
            "l10n_ph_holder_id_number": "SC-1",
        }
        pwd_vals = {
            **holder_vals,
            "l10n_ph_discount_privilege_id": self.privilege_pwd.id,
            "l10n_ph_holder_name": "Abigail Dela Cruz",
            "l10n_ph_holder_id_number": "PWD-1",
        }
        regular_vals = {
            "tax_ids": self.tax_sale_12.ids,
            "discount": 0.0,
            "l10n_ph_persons_sharing": 3,
            "l10n_ph_discount_privilege_id": False,
            "l10n_ph_holder_name": False,
            "l10n_ph_holder_id_number": False,
            "l10n_ph_special_discount_amount": 0.0,
        }
        self.assertRecordValues(order.lines.sorted("id"), [
            {**regular_vals, "product_id": self.pizza.id, "qty": 1.2, "price_subtotal": 1200.0},
            {**regular_vals, "product_id": self.soda.id, "qty": 2.4, "price_subtotal": 240.0},
            {
                **sc_vals,
                "product_id": self.pizza.id,
                "qty": 0.4,
                "price_subtotal": 320.0,
                "l10n_ph_special_discount_amount": 80.0,
            },
            {
                **pwd_vals,
                "product_id": self.pizza.id,
                "qty": 0.4,
                "price_subtotal": 320.0,
                "l10n_ph_special_discount_amount": 80.0,
            },
            {
                **sc_vals,
                "product_id": self.soda.id,
                "qty": 0.8,
                "price_subtotal": 64.0,
                "l10n_ph_special_discount_amount": 16.0,
            },
            {
                **pwd_vals,
                "product_id": self.soda.id,
                "qty": 0.8,
                "price_subtotal": 64.0,
                "l10n_ph_special_discount_amount": 16.0,
            },
        ])
        # POS does not compute extra_tax_data from price_unit/discount/
        # tax_ids/qty: the split must refresh it on every share, or the
        # frontend's tax display crashes reading stale data.
        for line in order.lines:
            expected = self.env["account.tax"]._export_base_line_extra_tax_data(
                line._l10n_ph_prepare_taxed_base_line(),
            )
            # fields.Json stores/reads an empty dict back as False.
            self.assertEqual(line.extra_tax_data, expected or False)
        # 3 regular shares at 1,120 VAT included, the others exempt and 20% off.
        self.assertRecordValues(order, [{"amount_total": 2380.8, "amount_tax": 172.8}])

    def test_all_holders_no_regular_share_reuses_original_line(self):
        """When every diner is an ID holder, the original line is reused for
        the first holder instead of being shrunk to zero and orphaned, and
        the other holders' shares still record the pre-privilege values. A manual
        discount already on the line is replaced by the privilege's, and kept
        as the original discount."""
        order = self._create_order([(self.pizza, 2.0)])
        original_line = order.lines
        original_line.discount = 10.0

        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz"),
            ],
            num_persons_sharing=2,
        )

        self.assertIn(original_line, order.lines)
        self.assertRecordValues(order.lines.sorted("id"), [
            {
                "qty": 1.0,
                "discount": 20.0,
                "price_unit": 1000.0,
                "tax_ids": self.tax_sale_0_exempt_sc_pwd.ids,
                "l10n_ph_original_discount": 10.0,
                "l10n_ph_original_price_unit": 1000.0,
                "l10n_ph_original_tax_ids": self.tax_sale_12.ids,
                # Not repriced by the POS from the pricelist.
                "price_type": "manual",
                "l10n_ph_discount_privilege_id": privilege.id,
                "l10n_ph_special_discount_amount": 200.0,
                "l10n_ph_regular_discount_amount": 0.0,
            }
            for privilege in (self.privilege_sc, self.privilege_pwd)
        ])

    def test_split_conserves_quantity_with_rounding(self):
        """Quantities are stored with the "Product Unit" precision: rounding
        each share on its own must never add or lose quantity, the last
        holder share absorbing the residual."""
        for qty, num_persons, privileges, expected_qtys in (
            (2.0, 3, [self.privilege_sc, self.privilege_pwd], [0.67, 0.67, 0.66]),  # 0.67 x 3 would be 2.01
            (1.0, 3, [self.privilege_sc, self.privilege_pwd, self.privilege_sc], [0.33, 0.33, 0.34]),  # 0.99
        ):
            with self.subTest(qty=qty, num_persons=num_persons, num_holders=len(privileges)):
                order = self._create_order([(self.pizza, qty)])
                order._l10n_ph_apply_discount_privileges(
                    holders_vals=[self._holder_vals(privilege) for privilege in privileges],
                    num_persons_sharing=num_persons,
                )
                self.assertRecordValues(order.lines.sorted("id"), [{"qty": qty} for qty in expected_qtys])

    # ============================================================
    #  Single-line target (spec: "one product selected")
    # ============================================================

    def test_rpc_target_line_only_splits_that_line(self):
        """Spec section 4 "Specific Items": a line ordered exclusively for the
        ID holder is fully attributed to them (num_persons_sharing=1 for that
        line's own invocation); the rest of the order is untouched. Through
        the RPC the line is found by uuid, and the answer is the order's
        records, in the shape the frontend merges into its local store."""
        order = self._create_order([(self.pizza, 2.0), (self.soda, 4.0)])
        pizza_line = order.lines[0]
        holder_vals = self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")

        result = order.l10n_ph_apply_discount_privileges(
            holders_vals=[holder_vals], num_persons_sharing=1, target_line_uuid=pizza_line.uuid,
        )

        self.assertRecordValues(order.lines, [
            {"product_id": self.pizza.id, "qty": 2.0, "l10n_ph_discount_privilege_id": self.privilege_sc.id},
            {"product_id": self.soda.id, "qty": 4.0, "l10n_ph_discount_privilege_id": False},
        ])
        self.assertIn("pizza", order.message_ids[0].body.lower())
        self.assertEqual(set(result), {
            "pos.order", "pos.order.line", "pos.prep.line", "res.partner", "product.attribute.custom.value",
        })
        self.assertEqual([vals["id"] for vals in result["pos.order"]], order.ids)
        self.assertCountEqual([vals["id"] for vals in result["pos.order.line"]], order.lines.ids)
        self.assertEqual([vals["id"] for vals in result["res.partner"]], [holder_vals["partner_id"]])
        # The POS reads the order again after an answer that got lost.
        self.assertEqual(order.l10n_ph_read_discount_privilege_data(), result)

    def test_target_line_pro_rates_by_real_headcount(self):
        """Spec section 8.2 "Group Orders, one product selected": selecting a line
        still pro-rates it by the table's actual headcount. Unlike the
        "Specific Items" case, the selected line itself still gets a regular
        share alongside the holder shares; the rest of the order is untouched."""
        order = self._create_order([(self.pizza, 5.0), (self.soda, 4.0)])

        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz"),
            ],
            num_persons_sharing=5,
            target_line=order.lines[0],
        )

        self.assertRecordValues(order.lines.sorted("id"), [
            {"product_id": self.pizza.id, "qty": 3.0, "l10n_ph_discount_privilege_id": False},
            {"product_id": self.soda.id, "qty": 4.0, "l10n_ph_discount_privilege_id": False},
            {"product_id": self.pizza.id, "qty": 1.0, "l10n_ph_discount_privilege_id": self.privilege_sc.id},
            {"product_id": self.pizza.id, "qty": 1.0, "l10n_ph_discount_privilege_id": self.privilege_pwd.id},
        ])

    def test_composability_specific_item_then_whole_order(self):
        """Case 2 (exclusive item) followed by case 1 (shared remainder) on
        the same order: the already-privileged line must be excluded from
        the second, whole-order application."""
        order = self._create_order([(self.pizza, 2.0), (self.soda, 4.0)])

        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
            num_persons_sharing=1,
            target_line=order.lines[0],
        )
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz", "PWD-1")],
            num_persons_sharing=5,
        )

        self.assertRecordValues(order.lines.sorted("id"), [
            {"product_id": self.pizza.id, "qty": 2.0, "l10n_ph_discount_privilege_id": self.privilege_sc.id},
            {"product_id": self.soda.id, "qty": 3.2, "l10n_ph_discount_privilege_id": False},
            {"product_id": self.soda.id, "qty": 0.8, "l10n_ph_discount_privilege_id": self.privilege_pwd.id},
        ])

    # ============================================================
    #  Validation
    # ============================================================

    def test_invalid_requests_rejected(self):
        """Each request the engine can't honor is refused for its own reason."""
        Partner = self.env["res.partner"]
        holder = self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")
        pwd_holder = self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz", "PWD-1")
        without_id = {"privilege_id": self.privilege_sc.id, "partner_id": Partner.create({"name": "No ID"}).id}
        pwd_id_only = {
            "privilege_id": self.privilege_sc.id,
            "partner_id": Partner.create({
                "name": "PWD only",
                "additional_identifiers": {"PH_PWD_ID": "PWD-9"},
            }).id,
        }
        archived_privilege = self.privilege_sc.copy({"name": "Archived", "active": False})

        def new_order(order_lines=None):
            return self._create_order(order_lines or [(self.pizza, 1.0)])

        paid_order = new_order()
        paid_order.state = "paid"
        privileged_order = new_order()
        privileged_order._l10n_ph_apply_discount_privileges([holder], 1, privileged_order.lines)
        paid_privileged_order = new_order()
        paid_privileged_order._l10n_ph_apply_discount_privileges([holder], 1)
        paid_privileged_order.state = "paid"
        exempt_order = new_order([(self.soda, 2.0)])
        exempt_order.lines.tax_ids = self.tax_sale_0_exempt_sc_pwd
        combo_order, combo_line, combo_child = self._create_combo_order()

        def apply(order, **kwargs):
            return order._l10n_ph_apply_discount_privileges(**kwargs)

        def rpc_apply(order, **kwargs):
            return order.l10n_ph_apply_discount_privileges(**kwargs)

        def rpc_remove(order, **kwargs):
            return order.l10n_ph_remove_discount_privilege(**kwargs)

        cases = [
            ("no holders", new_order(), apply, {"holders_vals": [], "num_persons_sharing": 1}, "at least one discount"),
            (
                "fewer persons than IDs",
                new_order(),
                apply,
                {"holders_vals": [holder, pwd_holder], "num_persons_sharing": 1},
                "at least the number of IDs",
            ),
            *(
                (
                    f"headcount {num_persons_sharing!r}",
                    new_order(),
                    apply,
                    {"holders_vals": [holder], "num_persons_sharing": num_persons_sharing},
                    "must be a whole number",
                )
                for num_persons_sharing in (True, 2.5, "2")
            ),
            (
                "quantity too small to share",
                new_order([(self.pizza, 0.5)]),
                apply,
                {"holders_vals": [holder], "num_persons_sharing": 100},
                "too small to be shared",
            ),
            (
                "paid order",
                paid_order,
                rpc_apply,
                {"holders_vals": [holder], "num_persons_sharing": 1},
                "only be applied to unpaid",
            ),
            (
                "line of another order",
                new_order(),
                apply,
                {"holders_vals": [holder], "num_persons_sharing": 1, "target_line": new_order().lines},
                "does not belong to this order",
            ),
            (
                "unknown line uuid",
                new_order(),
                rpc_apply,
                {"holders_vals": [holder], "num_persons_sharing": 1, "target_line_uuid": "not-a-line"},
                "does not belong to this order",
            ),
            (
                "line already privileged",
                privileged_order,
                apply,
                {"holders_vals": [pwd_holder], "num_persons_sharing": 1, "target_line": privileged_order.lines},
                "already has a discount privilege",
            ),
            (
                "no line left",
                privileged_order,
                apply,
                {"holders_vals": [pwd_holder], "num_persons_sharing": 1},
                "no more lines",
            ),
            (
                "privilege covering no line",
                exempt_order,
                apply,
                {"holders_vals": [holder], "num_persons_sharing": 2},
                "do not apply to any line",
            ),
            (
                "combo line",
                combo_order,
                apply,
                {"holders_vals": [holder], "num_persons_sharing": 1, "target_line": combo_line},
                "combo",
            ),
            (
                "combo child line",
                combo_order,
                apply,
                {"holders_vals": [holder], "num_persons_sharing": 1, "target_line": combo_child},
                "combo",
            ),
            (
                "archived privilege",
                new_order(),
                apply,
                {
                    "holders_vals": [{**holder, "privilege_id": archived_privilege.id}],
                    "num_persons_sharing": 1,
                },
                "Select a discount privilege",
            ),
            (
                "no contact",
                new_order(),
                apply,
                {"holders_vals": [{**holder, "partner_id": False}], "num_persons_sharing": 1},
                "Select the contact",
            ),
            (
                "contact without ID",
                new_order(),
                apply,
                {"holders_vals": [without_id], "num_persons_sharing": 1},
                "has no Senior Citizen ID",
            ),
            (
                "contact with another ID",
                new_order(),
                apply,
                {"holders_vals": [pwd_id_only], "num_persons_sharing": 1},
                "has no Senior Citizen ID",
            ),
            (
                "representative without ID",
                new_order(),
                apply,
                {"holders_vals": [{**holder, "representative_name": "Maria Dela Cruz"}], "num_persons_sharing": 1},
                "representative's name and ID are required",
            ),
            (
                "undo on a regular line",
                new_order(),
                rpc_remove,
                {"line_uuid": new_order().lines.uuid},
                "has no discount privilege",
            ),
            (
                "undo on a paid order",
                paid_privileged_order,
                rpc_remove,
                {"line_uuid": paid_privileged_order.lines.uuid},
                "only be removed from unpaid",
            ),
        ]
        for label, order, call, kwargs, message in cases:
            with self.subTest(label), self.assertRaisesRegex(UserError, message):
                call(order, **kwargs)
        self.assertFalse(
            (paid_order | exempt_order | combo_order).lines.l10n_ph_discount_privilege_id,
            "a refused request leaves its order as it was",
        )
        self.assertEqual(privileged_order.lines.l10n_ph_discount_privilege_id, self.privilege_sc)

    def test_combo_lines_are_not_split(self):
        """A combo and its items are sold as a whole: splitting an item's
        quantity would desync it from its parent."""
        order, combo_line, combo_child = self._create_combo_order()
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=2,
        )
        self.assertRecordValues(order.lines.sorted("id"), [
            {"product_id": combo_line.product_id.id, "qty": 1.0, "l10n_ph_discount_privilege_id": False},
            {"product_id": self.soda.id, "qty": 1.0, "l10n_ph_discount_privilege_id": False},
            {"product_id": self.pizza.id, "qty": 1.0, "l10n_ph_discount_privilege_id": False},
            {"product_id": self.soda.id, "qty": 1.0, "l10n_ph_discount_privilege_id": self.privilege_sc.id},
        ])
        self.assertEqual(combo_child.combo_parent_id, combo_line)

    def test_non_goods_lines_are_not_split(self):
        """Global discounts, rewards, tips and service fees aren't goods sold
        to the ID holder: they are never split nor privileged."""
        order = self._create_order([(self.pizza, 2.0), (self.soda, 1.0)])
        tip_product = self.env["product.product"].create({"name": "Tip", "list_price": 50.0})
        self.config.tip_product_id = tip_product
        preset = self.env["pos.preset"].create({"name": "Dine in"})
        self.config.available_preset_ids = preset
        fee_line = self._add_order_line(order, preset.service_fee_product_id, 1.0)
        tip_line = self._add_order_line(order, tip_product, 1.0)
        discount_line = self.env["pos.order.line"].create({
            "order_id": order.id,
            "product_id": self.soda.id,
            "qty": 1.0,
            "price_unit": -100.0,
            "price_subtotal": -100.0,
            "price_subtotal_incl": -100.0,
        })
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=2,
        )
        self.assertRecordValues(fee_line | tip_line | discount_line, [
            {"qty": 1.0, "l10n_ph_discount_privilege_id": False},
            {"qty": 1.0, "l10n_ph_discount_privilege_id": False},
            {"qty": 1.0, "l10n_ph_discount_privilege_id": False},
        ])
        self.assertEqual(len(order.lines), 7, "pizza and soda split in 2 shares each")
        for line in (fee_line, tip_line):
            with self.subTest(line=line.product_id.name), self.assertRaisesRegex(UserError, "cannot be applied"):
                order._l10n_ph_apply_discount_privileges(
                    holders_vals=[self._holder_vals(self.privilege_pwd)],
                    num_persons_sharing=1,
                    target_line=line,
                )

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
    #  Order log
    # ============================================================

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
        self.assertRecordValues(order.lines, [{"is_edited": False}] * 2)
        self.assertRecordValues(order, [{"is_edited": False}])
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
        regular, holder_line = order.lines.sorted("id")
        self.assertEqual(self._get_sent_qty(holder_line), holder_line.qty)
        self.assertEqual(self._get_sent_qty(regular), 1.0)
        self.assertEqual(regular.qty, 2.0)
