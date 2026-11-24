# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.l10n_ph_pos.tests.common import TestPosDiscountPrivilegeCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegeLine(TestPosDiscountPrivilegeCommon):
    """
    Coverage of the privilege hooks of pos.order.line, and of what happens to a
    privileged share afterwards: ID holders, discounts and prices, access,
    refunds and undo (l10n_ph_remove_discount_privilege). The splitting itself
    is in test_discount_privilege_engine.
    """

    # ============================================================
    #  ID holders
    # ============================================================

    def test_holder_information_comes_from_contact(self):
        """An ID holder's name and ID number are taken from their contact, and
        recorded as presented at the time of sale (with their representative's
        when absent): editing the contact later on doesn't alter them."""
        order = self._create_order([(self.pizza, 2.0)])
        holder_vals = {
            **self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1"),
            "representative_name": "Maria Dela Cruz",
            "representative_id": "REP-1",
        }
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=2)
        partner = self.env["res.partner"].browse(holder_vals["partner_id"])
        partner.write({"name": "Juan P. Dela Cruz", "additional_identifiers": {"PH_SC_ID": "SC-2"}})
        self.assertRecordValues(order.lines.sorted("id"), [
            {
                "l10n_ph_holder_partner_id": False,
                "l10n_ph_holder_name": False,
                "l10n_ph_holder_id_number": False,
                "l10n_ph_holder_representative_name": False,
                "l10n_ph_holder_representative_id": False,
            },
            {
                "l10n_ph_holder_partner_id": partner.id,
                "l10n_ph_holder_name": "Juan Dela Cruz",
                "l10n_ph_holder_id_number": "SC-1",
                "l10n_ph_holder_representative_name": "Maria Dela Cruz",
                "l10n_ph_holder_representative_id": "REP-1",
            },
        ])

    def test_rpc_ignores_unknown_holder_fields(self):
        order = self._create_order([(self.pizza, 1.0)])
        other_order = self._create_order([(self.soda, 1.0)])
        holder_vals = self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")
        order.l10n_ph_apply_discount_privileges(
            holders_vals=[{
                **holder_vals,
                "order_id": other_order.id,
                "price_unit": 0.0,
                "name": "Somebody Else",
                "id_number": "INJECTED",
                "l10n_ph_holder_id_number": "INJECTED",
            }],
            num_persons_sharing=1,
        )
        self.assertRecordValues(order.lines | other_order.lines, [
            {
                "product_id": self.pizza.id,
                "price_unit": 1000.0,
                "l10n_ph_discount_privilege_id": self.privilege_sc.id,
                "l10n_ph_holder_name": "Juan Dela Cruz",
                "l10n_ph_holder_id_number": "SC-1",
            },
            {
                "product_id": self.soda.id,
                "price_unit": 100.0,
                "l10n_ph_discount_privilege_id": False,
                "l10n_ph_holder_name": False,
                "l10n_ph_holder_id_number": False,
            },
        ])

    def test_one_privilege_per_person(self):
        """SC/PWD privileges can't be combined: a person (identified by their
        contact) presents a single ID per order, and nobody else can present it."""
        for case, first_holders, second_holders, message in (
            (
                "twice in the same application",
                [],
                [(self.privilege_sc, "Juan Dela Cruz", "SC-1"), (self.privilege_pwd, "Juan Dela Cruz", "PWD-1")],
                "can only present one ID",
            ),
            (
                "another privilege later on",
                [(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
                [(self.privilege_pwd, "Juan Dela Cruz", "PWD-1")],
                "already claims a discount privilege",
            ),
            (
                "the same privilege with another ID",
                [(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
                [(self.privilege_sc, "Juan Dela Cruz", "SC-2")],
                "already claims a discount privilege",
            ),
            (
                "somebody else's ID",
                [(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
                [(self.privilege_sc, "Maria Dela Cruz", "SC-1")],
                "already presented by someone else",
            ),
        ):
            with self.subTest(case=case):
                order = self._create_order([(self.pizza, 2.0), (self.soda, 2.0)])
                if first_holders:
                    order._l10n_ph_apply_discount_privileges(
                        holders_vals=[self._holder_vals(*holder) for holder in first_holders],
                        num_persons_sharing=2,
                        target_line=order.lines[0],
                    )
                # Created outside of assertRaises, which rolls back what happens in it.
                second_holders_vals = [self._holder_vals(*holder) for holder in second_holders]
                with self.assertRaisesRegex(UserError, message):
                    order._l10n_ph_apply_discount_privileges(
                        holders_vals=second_holders_vals,
                        num_persons_sharing=2,
                    )

    def test_holder_not_given_another_share_of_the_same_line(self):
        """Re-applying an ID holder on the whole order (e.g. for dishes ordered
        later) must not give them another share of the regular share left by
        their earlier split: they aren't among its persons anymore."""
        order = self._create_order([(self.pizza, 4.0)])
        holder_vals = self._holder_vals(self.privilege_sc, "Juan Dela Cruz")
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=4)
        pizza = order.lines[0]
        soda = self._add_order_line(order, self.soda, 2.0)
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=2)
        self.assertRecordValues(order.lines.sorted("id"), [
            {"product_id": self.pizza.id, "qty": 3.0, "l10n_ph_persons_sharing": 3, "l10n_ph_holder_name": False},
            {"product_id": self.pizza.id, "qty": 1.0, "l10n_ph_persons_sharing": 0, "l10n_ph_holder_name": "Juan Dela Cruz"},
            {"product_id": self.soda.id, "qty": 1.0, "l10n_ph_persons_sharing": 1, "l10n_ph_holder_name": False},
            {"product_id": self.soda.id, "qty": 1.0, "l10n_ph_persons_sharing": 0, "l10n_ph_holder_name": "Juan Dela Cruz"},
        ])
        self.assertEqual(order.lines[2], soda)
        with self.assertRaisesRegex(UserError, "already has their share"):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[holder_vals], num_persons_sharing=3, target_line=pizza,
            )

    def test_resplit_keeps_remaining_regular_headcount(self):
        """An ID presented later on (e.g. a forgotten PWD ID) is pro-rated
        among the regular persons still sharing the order, not the whole
        table again: 5 persons, SC applied first, then PWD."""
        order = self._create_order([(self.pizza, 5.0)])
        for privilege in (self.privilege_sc, self.privilege_pwd):
            order._l10n_ph_apply_discount_privileges(
                holders_vals=[self._holder_vals(privilege)],
                num_persons_sharing=5,
            )
        self.assertRecordValues(order.lines.sorted("id"), [
            {"qty": 3.0, "l10n_ph_persons_sharing": 3, "l10n_ph_discount_privilege_id": False},
            {"qty": 1.0, "l10n_ph_persons_sharing": 0, "l10n_ph_discount_privilege_id": self.privilege_sc.id},
            {"qty": 1.0, "l10n_ph_persons_sharing": 0, "l10n_ph_discount_privilege_id": self.privilege_pwd.id},
        ])

    # ============================================================
    #  Discounts and prices
    # ============================================================

    def test_privileged_line_cannot_be_discounted_again(self):
        """No double discounting: a privileged share's discount is its
        privilege's, whatever the POS sends."""
        order = self._create_order([(self.pizza, 1.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=1,
        )
        with self.assertRaisesRegex(ValidationError, "can't be given another discount"):
            order.lines.discount = 30.0

    def test_privileged_line_requires_holder_information(self):
        order = self._create_order([(self.pizza, 2.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=2,
        )
        regular_line, holder_line = order.lines
        for vals in (
            {"l10n_ph_holder_partner_id": False},
            {"l10n_ph_holder_name": False},
            {"l10n_ph_holder_id_number": False},
            {"l10n_ph_holder_representative_name": "Maria Dela Cruz"},
        ):
            with self.subTest(vals=vals), self.assertRaisesRegex(ValidationError, "ID holder's contact"):
                holder_line.write(vals)
        # Any line a device syncs is saved as is: a privilege alone is not enough.
        with self.assertRaisesRegex(ValidationError, "ID holder's contact"):
            regular_line.write({
                "l10n_ph_discount_privilege_id": self.privilege_sc.id,
                "discount": self.privilege_sc.discount_amount * 100.0,
            })

    def test_special_privilege_needs_no_id_and_discounts_the_total(self):
        """A special discount has no ID document and no VAT exemption: it is
        taken off the tax-included price, and reported as such."""
        privilege = self.privilege_sc.copy({
            "name": "Special 20%",
            "discount_type": "special",
            "fiscal_position_id": False,
        })
        partner = self.env["res.partner"].create({"name": "Pedro Penduko"})
        order = self._create_order([(self.pizza, 1.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[{"privilege_id": privilege.id, "partner_id": partner.id}],
            num_persons_sharing=1,
        )
        self.assertRecordValues(order.lines, [{
            "l10n_ph_discount_privilege_id": privilege.id,
            "l10n_ph_holder_name": "Pedro Penduko",
            "l10n_ph_holder_id_number": False,
            "tax_ids": self.tax_sale_12.ids,
            "discount": 20.0,
            "l10n_ph_special_discount_amount": 224.0,
        }])

    def test_price_included_by_company_setting(self):
        """The VAT is removed from the price of a holder share when the tax is
        included in price through the company's setting too, not only through
        the tax's own override."""
        self.company.account_price_include = "tax_included"
        self.tax_sale_12.price_include_override = False
        self.assertTrue(self.tax_sale_12.price_include)
        order = self._create_order([(self.soda, 1.0)])
        self.assertRecordValues(order.lines, [{"price_subtotal_incl": 100.0}])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=1,
        )
        self.assertAlmostEqual(order.lines.price_unit, 100.0 / 1.12)
        self.assertRecordValues(order.lines, [{
            "l10n_ph_original_price_unit": 100.0,
            "price_subtotal_incl": 71.43,
        }])

    def test_combo_line_has_no_discount_amounts(self):
        _order, combo_line, _combo_child = self._create_combo_order()
        self.assertTrue(combo_line._l10n_ph_skip_discount_amounts())
        self.assertRecordValues(combo_line, [{
            "l10n_ph_special_discount_amount": 0.0,
            "l10n_ph_regular_discount_amount": 0.0,
        }])

    def test_gross_price_details_ignore_discount(self):
        """The gross recompute must ignore any discount already on the line."""
        line = self._create_order([(self.pizza, 2.0)]).lines
        line.discount = 50.0
        # No privilege applied yet: the line's own price_subtotal/incl were
        # computed without a discount, so the gross recompute matches them.
        self.assertEqual(
            tuple(round(amount, 2) for amount in line._l10n_ph_get_discount_price_details()),
            (2000.0, 0.0, 2240.0, 0.0),
        )

    # ============================================================
    #  Access
    # ============================================================

    def test_privileges_applied_and_removed_by_a_pos_user(self):
        """The RPCs are called by the cashier, who isn't a manager: they need
        no more than the POS user's access."""
        pos_user = new_test_user(self.env, login="ph_pos_user", groups="point_of_sale.group_pos_user")
        order = self._create_order([(self.pizza, 2.0)])
        order_as_user = order.with_user(pos_user)
        order_as_user.l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc)],
            num_persons_sharing=2,
        )
        self.assertRecordValues(order.lines.sorted("id"), [
            {"qty": 1.0, "l10n_ph_discount_privilege_id": False},
            {"qty": 1.0, "l10n_ph_discount_privilege_id": self.privilege_sc.id},
        ])
        order_as_user.l10n_ph_remove_discount_privilege(order.lines[1].uuid)
        self.assertRecordValues(order.lines, [{"qty": 2.0, "l10n_ph_discount_privilege_id": False}])

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
        refund_line = self.env["pos.order.line"].create({
            "order_id": self._create_order([(self.soda, 1.0)]).id,
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
        regular, sc_line, pwd_line = order.lines.sorted("id")
        result = order.l10n_ph_remove_discount_privilege(sc_line.uuid)

        self.assertFalse(sc_line.exists())
        self.assertNotIn(sc_line.id, [line_vals["id"] for line_vals in result["pos.order.line"]])
        self.assertRecordValues(regular | pwd_line, [
            {"qty": 2.0, "l10n_ph_persons_sharing": 2, "price_subtotal": 2000.0},
            {"qty": 1.0, "l10n_ph_persons_sharing": 0, "price_subtotal": 800.0},
        ])
        self.assertRecordValues(order, [{"amount_total": 2000.0 * 1.12 + 800.0}])
        # Its quantity sent to the kitchen comes back with it.
        self.assertEqual(self._get_sent_qty(regular), 2.0)
        self.assertIn("Discount privilege of Juan Dela Cruz removed", order.message_ids[0].body)

    def test_remove_privilege_without_regular_share(self):
        """With no regular share to give it back to, the share becomes a
        regular line of its own again, priced and taxed as before the split,
        with the price type it had."""
        for price_type in ("original", "manual", "automatic"):
            with self.subTest(price_type=price_type):
                order = self._create_order([(self.pizza, 1.0)])
                order.lines.write({"discount": 10.0, "price_type": price_type})
                order._l10n_ph_apply_discount_privileges(
                    holders_vals=[self._holder_vals(self.privilege_sc)],
                    num_persons_sharing=1,
                )
                self.assertEqual(order.lines.price_type, "manual", "never repriced from the pricelist")
                order.l10n_ph_remove_discount_privilege(order.lines.uuid)
                self.assertRecordValues(order.lines, [{
                    "qty": 1.0,
                    "price_unit": 1000.0,
                    "discount": 10.0,
                    "price_type": price_type,
                    "l10n_ph_original_price_type": False,
                    "tax_ids": self.tax_sale_12.ids,
                    "l10n_ph_discount_privilege_id": False,
                    "l10n_ph_holder_partner_id": False,
                    "l10n_ph_holder_name": False,
                    "l10n_ph_persons_sharing": 1,
                    "price_subtotal": 900.0,
                }])

    def test_remove_privilege_when_regular_share_became_privileged(self):
        """When the last regular person claims a privilege too, the regular
        share is reused for them: the first ID holder's share can't be given
        back to it, and becomes a regular line of its own."""
        order = self._create_order([(self.pizza, 2.0)])
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz")],
            num_persons_sharing=2,
        )
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz")],
            num_persons_sharing=2,
        )
        reused_line, sc_line = order.lines.sorted("id")
        self.assertEqual(reused_line.l10n_ph_discount_privilege_id, self.privilege_pwd)

        order.l10n_ph_remove_discount_privilege(sc_line.uuid)

        self.assertRecordValues(reused_line | sc_line, [
            {
                "qty": 1.0,
                "l10n_ph_discount_privilege_id": self.privilege_pwd.id,
                "l10n_ph_holder_name": "Abigail Dela Cruz",
                "l10n_ph_persons_sharing": 1,
                "tax_ids": self.tax_sale_0_exempt_sc_pwd.ids,
                "discount": 20.0,
            },
            {
                "qty": 1.0,
                "l10n_ph_discount_privilege_id": False,
                "l10n_ph_holder_name": False,
                "l10n_ph_persons_sharing": 1,
                "tax_ids": self.tax_sale_12.ids,
                "discount": 0.0,
            },
        ])
