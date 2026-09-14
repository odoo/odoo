from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestPurchaseTeam(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        cls.buyer_own = cls._new_buyer("buyer_own", "purchase.group_purchase_user")
        cls.buyer_team = cls._new_buyer(
            "buyer_team", "purchase_team.group_purchase_user_team"
        )
        cls.mate = cls._new_buyer("mate", "purchase.group_purchase_user")
        cls.outsider = cls._new_buyer("outsider", "purchase.group_purchase_user")
        cls.buyer_all = cls._new_buyer("buyer_all", "purchase.group_purchase_user_all")
        Team = cls.env["team.team"].sudo()
        cls.team = Team.create(
            {
                "name": "Raw materials",
                "use_purchase": True,
                "company_id": company.id,
                "member_ids": [(6, 0, (cls.buyer_team | cls.mate).ids)],
            }
        )
        cls.other_team = Team.create(
            {
                "name": "Packaging",
                "use_purchase": True,
                "company_id": company.id,
                "member_ids": [(6, 0, cls.outsider.ids)],
            }
        )
        cls.sales_only = Team.sudo().create(
            {"name": "Not buying", "company_id": company.id, "member_ids": []}
        )
        cls.vendor = cls.env["res.partner"].create({"name": "Vendor"})
        Order = cls.env["purchase.order"]
        cls.order_mate = Order.create(
            {"partner_id": cls.vendor.id, "user_id": cls.mate.id}
        )
        cls.order_outsider = Order.create(
            {"partner_id": cls.vendor.id, "user_id": cls.outsider.id}
        )
        cls.order_nobody = Order.create({"partner_id": cls.vendor.id, "user_id": False})

    @classmethod
    def _new_buyer(cls, login, group):
        return mail_new_test_user(
            cls.env,
            login=login,
            company_id=cls.env.company.id,
            groups=f"base.group_user,{group}",
        )

    def _visible_orders(self, user):
        orders = self.order_mate | self.order_outsider | self.order_nobody
        return (
            self.env["purchase.order"]
            .with_user(user)
            .search([("id", "in", orders.ids)])
        )

    def test_an_order_takes_its_buyers_purchase_team(self):
        self.assertEqual(self.order_mate.team_id, self.team)
        self.assertEqual(self.order_outsider.team_id, self.other_team)
        self.assertFalse(self.order_nobody.team_id)

    def test_changing_the_buyer_moves_the_order_to_the_new_buyers_team(self):
        self.order_mate.user_id = self.outsider
        self.assertEqual(self.order_mate.team_id, self.other_team)

    def test_a_team_without_the_purchase_usage_is_never_proposed(self):
        self.sales_only.member_ids = self.buyer_own
        order = self.env["purchase.order"].create(
            {"partner_id": self.vendor.id, "user_id": self.buyer_own.id}
        )
        self.assertFalse(order.team_id)

    def test_own_documents_see_their_orders_and_unowned_ones(self):
        order = self.env["purchase.order"].create(
            {"partner_id": self.vendor.id, "user_id": self.buyer_own.id}
        )
        orders = order | self.order_mate | self.order_outsider | self.order_nobody
        visible = (
            self.env["purchase.order"]
            .with_user(self.buyer_own)
            .search([("id", "in", orders.ids)])
        )
        self.assertEqual(set(visible.ids), {order.id, self.order_nobody.id})

    def test_team_documents_see_their_teammates_orders(self):
        self.assertEqual(
            set(self._visible_orders(self.buyer_team).ids),
            {self.order_mate.id, self.order_nobody.id},
        )

    def test_all_documents_see_every_order(self):
        self.assertEqual(
            set(self._visible_orders(self.buyer_all).ids),
            {self.order_mate.id, self.order_outsider.id, self.order_nobody.id},
        )

    def test_leaving_the_team_takes_its_documents_away_at_once(self):
        self.team.member_ids = self.mate
        self.assertEqual(
            set(self._visible_orders(self.buyer_team).ids), {self.order_nobody.id}
        )

    def test_the_report_carries_the_team(self):
        self.env["purchase.order.line"].create(
            {
                "order_id": self.order_mate.id,
                "product_id": self.product_a.id,
                "product_qty": 1,
                "price_unit": 10,
            }
        )
        self.env.flush_all()
        lines = self.env["purchase.report"].search([("team_id", "=", self.team.id)])
        self.assertEqual(lines.order_reference, self.order_mate)

    def test_a_context_team_of_another_usage_is_not_an_orders_team(self):
        order = (
            self.env["purchase.order"]
            .with_context(default_team_id=self.sales_only.id)
            .create({"partner_id": self.vendor.id, "user_id": self.mate.id})
        )

        self.assertEqual(order.team_id, self.team)

    def test_an_order_takes_a_purchase_team_of_its_own_company_only(self):
        company_2 = self.setup_other_company()["company"]
        self.mate.company_ids |= company_2
        team_2 = self.env["team.team"].create(
            {
                "name": "Raw materials 2",
                "use_purchase": True,
                "company_id": company_2.id,
            }
        )
        self.env["team.member"].create({"team_id": team_2.id, "user_id": self.mate.id})

        order = (
            self.env["purchase.order"]
            .with_company(company_2)
            .create(
                {
                    "partner_id": self.vendor.id,
                    "user_id": self.mate.id,
                    "company_id": company_2.id,
                }
            )
        )

        self.assertEqual(order.team_id, team_2)
        order.company_id = self.env.company
        self.assertEqual(order.team_id, self.team)

    def test_team_documents_see_orders_filed_under_their_team(self):
        self.order_outsider.team_id = self.team

        self.assertIn(self.order_outsider.id, self._visible_orders(self.buyer_team).ids)

    def test_team_documents_see_their_teammates_vendor_bills_only(self):
        Move = self.env["account.move"]
        bills = Move.create(
            [
                {
                    "move_type": "in_invoice",
                    "partner_id": self.vendor.id,
                    "invoice_user_id": user.id,
                    "invoice_date": "2026-01-01",
                }
                for user in (self.mate, self.outsider)
            ]
        )

        visible = Move.with_user(self.buyer_team).search([("id", "in", bills.ids)])

        self.assertEqual(visible.invoice_user_id, self.mate)
