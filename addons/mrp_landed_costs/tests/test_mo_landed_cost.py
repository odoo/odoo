from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMoLandedCost(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cost_product = cls.env["product.product"].create(
            {"name": "MRP LC product", "type": "service", "landed_cost_ok": True}
        )

    def _landed_cost(self):
        return self.env["stock.landed.cost"].create(
            {
                "cost_lines": [
                    Command.create(
                        {
                            "product_id": self.cost_product.id,
                            "price_unit": 100.0,
                            "split_method": "equal",
                        }
                    )
                ],
            }
        )

    def test_targeted_moves_empty_without_mo(self):
        cost = self._landed_cost()
        self.assertFalse(cost._get_targeted_move_ids())

    def test_finished_moves_of_a_manufacturing_order_are_targeted(self):
        mrp_product = self.env["product.product"].create(
            {"name": "MRP LC finished good", "type": "consu"}
        )
        production = self.env["mrp.production"].create({"product_id": mrp_product.id})
        cost = self._landed_cost()
        cost.mrp_production_ids = [Command.set(production.ids)]
        self.assertEqual(cost._get_targeted_move_ids(), production.move_finished_ids)
