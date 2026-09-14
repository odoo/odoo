from odoo import Command
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

    def _transfer(self, picking_type, product, user, **move_vals):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "user_id": user.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "location_id": picking_type.default_location_src_id.id,
                            "location_dest_id": picking_type.default_location_dest_id.id,
                            **move_vals,
                        }
                    )
                ],
            }
        )

    def test_a_transfer_keeps_its_team_when_its_operation_type_changes_team(self):
        self.type_in.team_id = self.other_team

        self.assertEqual(self.picking_team.team_id, self.team)

    def test_the_team_running_an_operation_type_sees_its_transfers(self):
        self.type_out.team_id = self.team

        self.assertEqual(self.picking_stranger.team_id, self.other_team)
        self.assertIn(self.picking_stranger.id, self._visible(self.user_team))

    def test_a_context_team_of_another_usage_is_not_a_transfers_team(self):
        sales = self.env["team.team"].create({"name": "Sales"})

        picking = (
            self.env["stock.picking"]
            .with_context(default_team_id=sales.id)
            .create({"picking_type_id": self.type_in.id})
        )

        self.assertEqual(picking.team_id, self.team)

    def test_a_batch_takes_the_one_team_of_its_transfers(self):
        self.type_out.team_id = False
        batch = self.env["stock.picking.batch"].create(
            {"picking_ids": [Command.set(self.picking_mate.ids)]}
        )
        self.assertEqual(batch.team_id, self.other_team)

        self.picking_stranger.team_id = self.team
        batch.picking_ids |= self.picking_stranger

        self.assertFalse(batch.team_id)
        self.picking_team.team_id = self.other_team
        inbound = self.env["stock.picking.batch"].create(
            {"picking_ids": [Command.set(self.picking_team.ids)]}
        )
        self.assertEqual(inbound.team_id, self.other_team)

    def test_validating_a_transfer_frees_a_reservation_the_user_cannot_see(self):
        product = self.env["product.product"].create(
            {"name": "Pallet", "is_storable": True}
        )
        self.env["stock.quant"]._update_available_quantity(
            product, self.type_out.default_location_src_id, 1
        )
        hidden = self._transfer(self.type_out, product, self.stranger)
        hidden.action_assign()
        self.assertEqual(hidden.state, "assigned")
        mine = self._transfer(self.type_out, product, self.user_team)
        mine.action_confirm()

        mine = mine.with_user(self.user_team)
        mine.move_ids.quantity = 1
        mine.move_ids.picked = True
        mine.button_validate()

        self.assertEqual(mine.state, "done")
        self.assertNotEqual(hidden.state, "assigned")

    def test_validating_a_receipt_reserves_a_delivery_the_user_cannot_see(self):
        product = self.env["product.product"].create(
            {"name": "Barrel", "is_storable": True}
        )
        receipt = self._transfer(self.type_in, product, self.mate)
        hidden = self._transfer(
            self.type_out,
            product,
            self.stranger,
            procure_method="make_to_order",
            move_orig_ids=[Command.set(receipt.move_ids.ids)],
        )
        (receipt | hidden).action_confirm()
        self.assertEqual(hidden.state, "waiting")

        receipt = receipt.with_user(self.user_team)
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        self.assertEqual(receipt.state, "done")
        self.assertEqual(hidden.state, "assigned")
