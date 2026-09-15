from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.sale_team.tests.common import SalesTeamSaleCommon


@tagged("post_install", "-at_install")
class TestSaleOrderTeam(SalesTeamSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sale_team_2 = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Test Sales Team (2)",
            }
        )
        cls.user_in_team = cls.env["res.users"].create(
            {
                "email": "team0user@example.com",
                "login": "team0user",
                "name": "User in Team 0",
            }
        )
        cls.sale_team.write({"member_ids": [4, cls.user_in_team.id]})
        cls.user_not_in_team = cls.env["res.users"].create(
            {
                "email": "noteamuser@example.com",
                "login": "noteamuser",
                "name": "User Not In Team",
            }
        )

    def test_compute_team_id_does_not_cross_companies(self):
        root_company = self.env["res.company"].create({"name": "F32 root company"})
        root_company.write(
            {
                "child_ids": [
                    Command.create({"name": "F32 company A"}),
                    Command.create({"name": "F32 company B"}),
                ]
            }
        )
        company_a, company_b = root_company.child_ids

        user = self.env["res.users"].create(
            {
                "name": "F32 multi-company salesman",
                "login": "f32_multi_company_salesman",
                "company_ids": [Command.set((company_a + company_b).ids)],
                "company_id": company_a.id,
            }
        )
        team_b = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "F32 team in company B",
                "company_id": company_b.id,
                "member_ids": [Command.set(user.ids)],
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "company_id": company_a.id,
                "user_id": user.id,
            }
        )
        self.assertNotEqual(
            order.team_id,
            team_b,
            "the order's team must not cross into another company",
        )

    def test_assign_sales_team_from_partner_user(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Customer of User In Team",
                "user_id": self.user_in_team.id,
            }
        )
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
            }
        )
        self.assertEqual(
            sale_order.team_id.id,
            self.sale_team.id,
            "Should assign to team of sales person",
        )

    def test_assign_sales_team_when_changing_user(self):
        sale_order = self.env["sale.order"].create(
            {
                "user_id": self.user_not_in_team.id,
                "partner_id": self.partner.id,
                "team_id": self.sale_team_2.id,
            }
        )
        sale_order.user_id = self.user_in_team
        self.assertEqual(
            sale_order.team_id.id,
            self.sale_team.id,
            "Should assign to team of sales person",
        )

    def test_keep_sales_team_when_changing_user_with_no_team(self):
        sale_order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "team_id": self.sale_team_2.id}
        )
        sale_order.user_id = self.user_not_in_team
        self.assertEqual(
            sale_order.team_id.id,
            self.sale_team_2.id,
            "Should not reset the team to default",
        )

    def test_compute_team_id_depends_on_company(self):
        AccountMove = self.env["account.move"]
        depends = self.env.registry.field_depends[AccountMove._fields["team_id"]]
        self.assertIn("company_id", depends)

    def test_common_orders_take_the_sales_team(self):
        self.assertEqual(self.empty_order.team_id, self.sale_team)
        self.assertEqual(self.sale_order.team_id, self.sale_team)


@tagged("-at_install", "post_install")
class TestSaleOrderTeamInvoicing(TestSaleCommon):
    def test_refund_salesteam(self):
        salesperson = self.user
        team1, team2 = self.env["team.team"].create(
            [
                {
                    "use_sale": True,
                    "name": "Team 1",
                    "member_ids": [Command.link(salesperson.id)],
                },
                {"use_sale": True, "name": "Team 2"},
            ]
        )
        self.assertEqual(salesperson.sale_team_id, team1)
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "user_id": salesperson.id,
                "team_id": team2.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_order_no"].id,
                            "product_qty": 5,
                            "price_unit": -10,
                            "tax_ids": False,
                        }
                    ),
                ],
            }
        )

        sale_order.action_confirm()
        invoice = sale_order._create_invoices(final=True)

        self.assertEqual(invoice.move_type, "out_refund")
        self.assertEqual(
            invoice.invoice_user_id,
            salesperson,
            "Invoice salesperson should be the same as the order's salesperson",
        )
        self.assertEqual(
            invoice.team_id,
            team2,
            "Invoice team should be the same as the order's team",
        )
