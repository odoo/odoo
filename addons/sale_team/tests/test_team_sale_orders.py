from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCrmTeamSales(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = cls.env["team.team"].create({"use_sale": True, "name": "Grind team"})
        cls.customer = cls.env["res.partner"].create({"name": "Team customer"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Team product",
                "type": "consu",
                "list_price": 100.0,
            }
        )

    def _orders(self, count, state=None):
        orders = self.env["sale.order"].create(
            [
                {
                    "partner_id": self.customer.id,
                    "team_id": self.team.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_qty": 1,
                            }
                        )
                    ],
                }
                for _dummy in range(count)
            ]
        )
        if state == "cancel":
            orders.action_cancel()
        return orders

    def test_order_count_ignores_cancelled(self):
        self._orders(2)
        self._orders(1, state="cancel")
        self.team.invalidate_recordset(["sale_order_count"])
        self.assertEqual(self.team.sale_order_count, 2)

    def test_team_without_orders_counts_zero(self):
        fresh = self.env["team.team"].create({"use_sale": True, "name": "Empty team"})
        self.assertEqual(fresh.sale_order_count, 0)

    def test_deleting_a_lightly_used_team_is_allowed(self):
        self._orders(4)
        self.team.invalidate_recordset(["sale_order_count"])
        self.team.unlink()
        self.assertFalse(self.team.exists())

    def test_deleting_an_actively_used_team_is_refused(self):
        self._orders(5)
        self.team.invalidate_recordset(["sale_order_count"])
        with self.assertRaises(UserError):
            self.team.unlink()

    def test_cancelled_orders_do_not_protect_the_team(self):
        self._orders(6, state="cancel")
        self.team.invalidate_recordset(["sale_order_count"])
        self.assertEqual(self.team.sale_order_count, 0)
        self.team.unlink()
        self.assertFalse(self.team.exists())

    def test_invoiced_is_zero_without_paid_invoices(self):
        self._orders(2)
        self.team.invalidate_recordset(["invoiced"])
        self.assertEqual(self.team.invoiced, 0.0)

    def test_invoiced_target_is_rounded(self):
        self.team.update_invoiced_target("1234.6")
        self.assertEqual(self.team.invoiced_target, 1235)
        self.team.update_invoiced_target("")
        self.assertEqual(self.team.invoiced_target, 0)

    def test_dashboard_button_follows_the_sales_context(self):
        in_sales = self.team.with_context(in_sales_app=True)
        in_sales._compute_dashboard_button_name()
        self.assertEqual(in_sales.dashboard_button_name, "Sales Analysis")

        action = in_sales.action_primary_channel_button()
        self.assertEqual(action["type"], "ir.actions.act_window")


@tagged("post_install", "-at_install")
class TestOrderTeamFollowsCompany(TransactionCase):
    def test_moving_an_order_to_another_company_moves_its_team(self):
        company_main = self.env.company
        company_2 = self.env["res.company"].create({"name": "Order Team Co2"})
        self.env["team.team"].search([]).action_archive()
        team_main, team_2 = self.env["team.team"].create(
            [
                {"use_sale": True, "name": "Main Team", "company_id": company_main.id},
                {"use_sale": True, "name": "Co2 Team", "company_id": company_2.id},
            ]
        )
        seller = self.env["res.users"].create(
            {
                "name": "Teamless Seller",
                "login": "teamless_seller",
                "company_id": company_main.id,
                "company_ids": [Command.set((company_main | company_2).ids)],
                "group_ids": [
                    Command.link(self.env.ref("sale.group_sale_salesman_all_leads").id)
                ],
            }
        )
        partner = self.env["res.partner"].create({"name": "Order Team Customer"})
        order = (
            self.env["sale.order"]
            .with_user(seller)
            .with_company(company_main)
            .create({"partner_id": partner.id, "user_id": seller.id})
        )
        self.assertEqual(order.team_id, team_main)

        order.with_context(
            allowed_company_ids=(company_2 | company_main).ids
        ).company_id = company_2
        self.assertEqual(order.sudo().team_id, team_2)
