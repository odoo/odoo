# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ph_pos.tests.common import make_holder_vals
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegeSessionClosing(TestPoSCommon):
    """
    The session's global invoice must keep the ID holder shares apart from
    the aggregated regular sales: one section per ID holder, with each
    share's privilege, while still balancing with the orders' payments.
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ph")
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        ChartTemplate = cls.env["account.chart.template"].with_company(cls.company)
        tax_sale_12 = ChartTemplate.ref("l10n_ph_tax_sale_12")
        cls.privilege_sc = ChartTemplate.ref("l10n_ph_discount_privilege_sc_20_vat_incl")
        cls.privilege_pwd = ChartTemplate.ref("l10n_ph_discount_privilege_pwd_20_vat_incl")
        cls.pizza = cls.create_product("Pizza", cls.categ_basic, 1000.0, tax_ids=tax_sale_12.ids)
        cls.water = cls.create_product("Free Water", cls.categ_basic, 0.0, tax_ids=tax_sale_12.ids)

    def test_global_invoice_sections_per_holder(self):
        session = self.open_new_session()
        draft_data = self.create_ui_order_data(
            [(self.pizza, 5), (self.water, 5)],
            payments=[],
            pos_order_ui_args={"state": "draft"},
        )
        privileged_order = self.env["pos.order"].browse(
            self.env["pos.order"].sync_from_ui([draft_data])["pos.order"][0]["id"],
        )
        privileged_order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                make_holder_vals(self.env, self.privilege_sc, "Juan Dela Cruz", "SC-1"),
                make_holder_vals(self.env, self.privilege_pwd, "Abigail Dela Cruz", "PWD-1"),
            ],
            num_persons_sharing=5,
        )
        privileged_order.add_payment({
            "pos_order_id": privileged_order.id,
            "session_id": session.id,
            "amount": privileged_order.amount_total,
            "payment_method_id": self.cash_pm1.id,
        })
        privileged_order.action_pos_order_paid()
        regular_order = self.env["pos.order"].browse(
            self.env["pos.order"].sync_from_ui([self.create_ui_order_data([(self.pizza, 1)])])["pos.order"][0]["id"],
        )
        orders = privileged_order + regular_order

        session.close_session_from_ui({self.cash_pm1.id: sum(orders.mapped("amount_paid"))})

        move = session.sale_move_ids
        self.assertEqual(move.state, "posted")
        self.assertAlmostEqual(move.amount_total, sum(orders.mapped("amount_total")), places=2)
        # 3 regular shares at 1,120 + 1 at 1,120 + 2 holder shares at 800.
        self.assertAlmostEqual(move.amount_total, 4 * 1120.0 + 2 * 800.0, places=2)

        sections = move.invoice_line_ids.filtered(lambda line: line.display_type == "line_section")
        self.assertEqual(sections.mapped("name"), [
            "Regular Orders",
            "ID HOLDER Juan Dela Cruz - ID Type: Senior Citizen ID - ID#: SC-1",
            "ID HOLDER Abigail Dela Cruz - ID Type: Person with Disability ID - ID#: PWD-1",
        ])
        holder_lines = move.invoice_line_ids.filtered("l10n_ph_discount_privilege_id")
        self.assertEqual(
            sorted(holder_lines.mapped(lambda line: (line.l10n_ph_discount_privilege_id.id, line.product_id.id))),
            sorted([
                (self.privilege_sc.id, self.pizza.id),
                (self.privilege_sc.id, self.water.id),
                (self.privilege_pwd.id, self.pizza.id),
                (self.privilege_pwd.id, self.water.id),
            ]),
            "each holder share appears once, zero-priced ones included",
        )
        self.assertAlmostEqual(sum(holder_lines.mapped("l10n_ph_special_discount_amount")), 400.0, places=2)
