from odoo.tests import TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestStockTeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_own = cls._new_user("stock_own", "stock_team.group_stock_user_own")
        cls.user_team = cls._new_user("stock_team", "stock_team.group_stock_user_team")
        cls.mate = cls._new_user("stock_mate")
        cls.stranger = cls._new_user("stock_stranger")
        cls.user_all = cls._new_user("stock_all")
        Team = cls.env["team.team"]
        cls.team = Team.create(
            {
                "name": "Receiving",
                "use_stock": True,
                "member_ids": [(6, 0, (cls.user_team | cls.mate).ids)],
            }
        )
        cls.other_team = Team.create(
            {
                "name": "Shipping",
                "use_stock": True,
                "member_ids": [(6, 0, cls.stranger.ids)],
            }
        )
        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.type_in = warehouse.in_type_id
        cls.type_out = warehouse.out_type_id
        cls.type_in.team_id = cls.team
        cls.type_out.team_id = cls.other_team
        Picking = cls.env["stock.picking"]
        cls.picking_team = Picking.create(
            {"picking_type_id": cls.type_in.id, "user_id": False}
        )
        cls.picking_mate = Picking.create(
            {"picking_type_id": cls.type_out.id, "user_id": cls.mate.id}
        )
        cls.picking_stranger = Picking.create(
            {"picking_type_id": cls.type_out.id, "user_id": cls.stranger.id}
        )
        cls.picking_own = Picking.create(
            {"picking_type_id": cls.type_out.id, "user_id": cls.user_own.id}
        )
        cls.pickings = (
            cls.picking_team | cls.picking_mate | cls.picking_stranger | cls.picking_own
        )

    @classmethod
    def _new_user(cls, login, restriction=None):
        groups = "base.group_user,stock.group_stock_user"
        return mail_new_test_user(
            cls.env,
            login=login,
            company_id=cls.env.company.id,
            groups=f"{groups},{restriction}" if restriction else groups,
        )

    def _visible(self, user, records=None):
        records = records or self.pickings
        return set(
            self.env[records._name]
            .with_user(user)
            .search([("id", "in", records.ids)])
            .ids
        )

    def test_a_transfer_takes_the_team_of_its_operation_type(self):
        self.assertEqual(self.picking_team.team_id, self.team)
        self.assertEqual(self.picking_mate.team_id, self.other_team)

    def test_own_documents_see_their_transfers_and_the_unassigned_ones(self):
        self.assertEqual(
            self._visible(self.user_own),
            {self.picking_team.id, self.picking_own.id},
        )

    def test_team_documents_see_their_teams_and_teammates_transfers(self):
        self.assertEqual(
            self._visible(self.user_team),
            {self.picking_team.id, self.picking_mate.id},
        )

    def test_an_inventory_user_without_a_restriction_sees_every_transfer(self):
        self.assertEqual(self._visible(self.user_all), set(self.pickings.ids))

    def test_an_administrator_is_never_restricted(self):
        self.assertEqual(
            self._visible(self.env.ref("base.user_admin")), set(self.pickings.ids)
        )

    def test_moves_follow_the_visibility_of_their_transfer(self):
        product = self.env["product.product"].create(
            {"name": "Crate", "is_storable": True}
        )
        moves = self.env["stock.move"].create(
            [
                {
                    "product_id": product.id,
                    "product_uom_qty": 1,
                    "picking_id": picking.id,
                    "location_id": picking.location_id.id,
                    "location_dest_id": picking.location_dest_id.id,
                }
                for picking in (self.picking_mate, self.picking_stranger)
            ]
        )
        self.assertEqual(
            self._visible(self.user_team, moves),
            {moves.filtered(lambda m: m.picking_id == self.picking_mate).id},
        )
