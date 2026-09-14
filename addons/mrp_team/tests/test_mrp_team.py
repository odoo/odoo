from odoo.tests import TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestMrpTeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_own = cls._new_user("mrp_own", "mrp_team.group_mrp_user_own")
        cls.user_team = cls._new_user("mrp_team", "mrp_team.group_mrp_user_team")
        cls.mate = cls._new_user("mrp_mate")
        cls.user_all = cls._new_user("mrp_all")
        cls.team = cls.env["team.team"].create(
            {
                "name": "Line 1",
                "use_mrp": True,
                "use_stock": True,
                "member_ids": [(6, 0, (cls.user_team | cls.mate).ids)],
            }
        )
        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.manufacture_type = warehouse.manu_type_id
        cls.manufacture_type.team_id = cls.team
        cls.product = cls.env["product.product"].create(
            {"name": "Bench", "is_storable": True}
        )
        Production = cls.env["mrp.production"]
        cls.mo_unassigned = Production.create(
            {"product_id": cls.product.id, "user_id": False}
        )
        cls.mo_mate = Production.create(
            {"product_id": cls.product.id, "user_id": cls.mate.id}
        )
        cls.other_type = cls.manufacture_type.copy(
            {"name": "Other manufacturing", "sequence_code": "MO2", "team_id": False}
        )
        cls.mo_stranger = Production.create(
            {
                "product_id": cls.product.id,
                "user_id": cls.user_all.id,
                "picking_type_id": cls.other_type.id,
            }
        )
        cls.productions = cls.mo_unassigned | cls.mo_mate | cls.mo_stranger

    @classmethod
    def _new_user(cls, login, restriction=None):
        groups = "base.group_user,mrp.group_mrp_user"
        return mail_new_test_user(
            cls.env,
            login=login,
            company_id=cls.env.company.id,
            groups=f"{groups},{restriction}" if restriction else groups,
        )

    def _visible(self, user):
        return set(
            self.env["mrp.production"]
            .with_user(user)
            .search([("id", "in", self.productions.ids)])
            .ids
        )

    def test_an_order_takes_the_manufacturing_team_of_its_operation_type(self):
        self.assertEqual(self.mo_mate.team_id, self.team)

    def test_a_team_without_the_manufacturing_usage_is_not_taken(self):
        stock_only = self.env["team.team"].create({"name": "Stock", "use_stock": True})
        self.manufacture_type.team_id = stock_only
        production = self.env["mrp.production"].create({"product_id": self.product.id})
        self.assertFalse(production.team_id)

    def test_own_documents_see_their_orders_and_unassigned_ones(self):
        self.assertEqual(self._visible(self.user_own), {self.mo_unassigned.id})

    def test_team_documents_see_their_teams_orders(self):
        self.assertEqual(
            self._visible(self.user_team),
            {self.mo_unassigned.id, self.mo_mate.id},
        )

    def test_all_documents_see_every_order(self):
        self.assertEqual(self._visible(self.user_all), set(self.productions.ids))

    def test_a_manufacturing_restriction_leaves_transfers_alone(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.manufacture_type.warehouse_id.out_type_id.id,
                "user_id": self.user_all.id,
            }
        )
        self.assertTrue(
            self.env["stock.picking"]
            .with_user(self.user_own)
            .search([("id", "=", picking.id)])
        )

    def test_an_order_keeps_its_team_when_its_operation_type_changes_team(self):
        other = self.env["team.team"].create({"name": "Line 2", "use_mrp": True})

        self.manufacture_type.team_id = other

        self.assertEqual(self.mo_mate.team_id, self.team)

    def test_the_team_running_an_operation_type_sees_its_orders(self):
        self.other_type.team_id = self.team

        self.assertFalse(self.mo_stranger.team_id)
        self.assertIn(self.mo_stranger.id, self._visible(self.user_team))

    def test_changing_the_operation_type_takes_the_new_types_team(self):
        self.other_type.team_id = self.env["team.team"].create(
            {"name": "Line 2", "use_mrp": True}
        )

        self.mo_mate.picking_type_id = self.other_type

        self.assertEqual(self.mo_mate.team_id, self.other_type.team_id)

    def test_a_context_team_of_another_usage_is_not_an_orders_team(self):
        sales = self.env["team.team"].create({"name": "Sales"})

        production = (
            self.env["mrp.production"]
            .with_context(default_team_id=sales.id)
            .create({"product_id": self.product.id})
        )

        self.assertEqual(production.team_id, self.team)
