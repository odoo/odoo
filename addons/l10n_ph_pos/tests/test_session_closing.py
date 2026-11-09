# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.l10n_ph_pos.tests.common import TestPosDiscountPrivilegeCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegeSessionClosing(TestPosDiscountPrivilegeCommon):
    """
    The session's global invoice must keep the ID holder shares apart from
    the aggregated regular sales: one section per ID holder, with each
    share's privilege, while still balancing with the orders' payments.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.water = cls.create_product("Free Water", cls.categ_basic, 0.0, tax_ids=cls.tax_sale_12.ids)

    def _create_paid_privileged_order(self, order_lines, holders_vals, num_persons_sharing, **kwargs):
        order = self._create_order(order_lines, **kwargs)
        order._l10n_ph_apply_discount_privileges(
            holders_vals=holders_vals,
            num_persons_sharing=num_persons_sharing,
        )
        order.add_payment({
            "pos_order_id": order.id,
            "session_id": self.pos_session.id,
            "amount": order.amount_total,
            "payment_method_id": self.cash_pm1.id,
        })
        order.action_pos_order_paid()
        return order

    def test_global_invoice_sections_per_holder(self):
        privileged_order = self._create_paid_privileged_order(
            [(self.pizza, 5), (self.water, 5)],
            [
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz", "PWD-1"),
            ],
            5,
        )
        regular_order = self.env["pos.order"].browse(
            self.env["pos.order"].sync_from_ui([self.create_ui_order_data([(self.pizza, 1)])])["pos.order"][0]["id"],
        )
        orders = privileged_order + regular_order

        self.pos_session.close_session_from_ui({self.cash_pm1.id: sum(orders.mapped("amount_paid"))})

        move = self.pos_session.sale_move_ids
        # 3 regular shares at 1,120 + 1 at 1,120 + 2 holder shares at 800.
        self.assertRecordValues(move, [{"state": "posted", "amount_total": 4 * 1120.0 + 2 * 800.0}])
        self.assertRecordValues(move.invoice_line_ids.filtered(lambda line: line.display_type == "line_section"), [
            {"name": "Regular Orders"},
            {"name": "ID HOLDER Juan Dela Cruz - ID Type: Senior Citizen ID - ID#: SC-1"},
            {"name": "ID HOLDER Abigail Dela Cruz - ID Type: Person with Disability ID - ID#: PWD-1"},
        ])
        # Each holder share appears once, zero-priced ones included.
        holder_lines = move.invoice_line_ids.filtered("l10n_ph_discount_privilege_id")
        self.assertRecordValues(
            holder_lines.sorted(lambda line: (line.l10n_ph_holder_name, line.product_id.name)),
            [
                {
                    "l10n_ph_discount_privilege_id": privilege.id,
                    "l10n_ph_holder_name": holder_name,
                    "product_id": product.id,
                    "l10n_ph_special_discount_amount": discount_amount,
                }
                for holder_name, privilege in (
                    ("Abigail Dela Cruz", self.privilege_pwd),
                    ("Juan Dela Cruz", self.privilege_sc),
                )
                for product, discount_amount in ((self.water, 0.0), (self.pizza, 200.0))
            ],
        )

    def test_invoice_after_closing_reverses_holder_share(self):
        """Invoicing an order once its session closed reverses its part of the
        closing entry: the ID holder share too, with its VAT exempt base."""
        order = self._create_paid_privileged_order(
            [(self.pizza, 2)],
            [self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
            2,
            customer=self.customer,
        )
        self.pos_session.close_session_from_ui({self.cash_pm1.id: order.amount_paid})
        self.assertTrue(order.is_globally_invoiced)

        order.action_pos_order_invoice()

        reversal = self.env["account.move"].search([("ref", "like", "Partial reversal")])
        self.assertRecordValues(reversal, [{"state": "posted"}])
        # The regular share (1,000, taxed) and the SC share (800, VAT exempt)
        # are each reversed on their own line, not on a balancing one.
        self.assertRecordValues(reversal.line_ids.filtered(lambda line: line.display_type == "product"), [
            {"tax_ids": self.tax_sale_12.ids, "debit": 1000.0},
            {"tax_ids": self.tax_sale_0_exempt_sc_pwd.ids, "debit": 800.0},
        ])

    def test_refund_after_closing_keeps_holder_share(self):
        """An order refunded once its session closed: the refund, paid and
        closed in the next session, reverses the ID holder share on its own
        line, with its privilege and holder."""
        order = self._create_paid_privileged_order(
            [(self.pizza, 2)],
            [self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
            2,
        )
        self.pos_session.close_session_from_ui({self.cash_pm1.id: order.amount_paid})
        self.open_new_session()
        refund = self.env["pos.order"].browse(order.refund()["res_id"])
        self.env["pos.make.payment"].with_context(active_ids=refund.ids, active_id=refund.id).create({
            "payment_method_id": self.cash_pm1.id,
        }).check()

        self.pos_session.close_session_from_ui({self.cash_pm1.id: refund.amount_paid})

        move = self.pos_session.refund_move_ids
        self.assertRecordValues(move, [{"state": "posted", "amount_total": 1000.0 + 800.0 + 120.0}])
        self.assertRecordValues(move.invoice_line_ids.filtered("l10n_ph_discount_privilege_id"), [{
            "l10n_ph_discount_privilege_id": self.privilege_sc.id,
            "l10n_ph_holder_name": "Juan Dela Cruz",
            "l10n_ph_holder_id_number": "SC-1",
            "quantity": 1.0,
            "tax_ids": self.tax_sale_0_exempt_sc_pwd.ids,
        }])
