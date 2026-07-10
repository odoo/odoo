# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestPosLoyaltyServiceFee(TestPointOfSaleHttpCommon):
    def test_service_fee_quantity_with_promotion(self):
        # A fixed service fee must stay editable when an automatic loyalty
        # promotion is applied: scaling its quantity must scale the fee, not
        # revert it to the default price while the promotion recomputes.
        self.env["loyalty.program"].search([]).write({"active": False})
        # Two distinct (0%) taxes put the two products in different tax groups, so
        # the fixed fee splits into two tax-group lines.
        tax_a = self.env["account.tax"].create({
            "name": "Tax A 0%",
            "amount": 0,
            "amount_type": "percent",
            "type_tax_use": "sale",
        })
        tax_b = self.env["account.tax"].create({
            "name": "Tax B 0%",
            "amount": 0,
            "amount_type": "percent",
            "type_tax_use": "sale",
        })
        self.env["product.product"].create({
            "name": "Big Item",
            "available_in_pos": True,
            "list_price": 50.0,
            "taxes_id": [Command.set(tax_a.ids)],
        })
        small_item = self.env["product.product"].create({
            "name": "Small Item",
            "available_in_pos": True,
            "list_price": 50.0,
            "taxes_id": [Command.set(tax_b.ids)],
        })
        self.env["loyalty.program"].create({
            "name": "Auto 10% on order",
            "program_type": "promotion",
            "trigger": "auto",
            "rule_ids": [Command.create({})],
            "reward_ids": [Command.create({
                "reward_type": "discount",
                "discount": 10,
                "discount_mode": "percent",
                "discount_applicability": "order",
            })],
        })
        preset = self.env["pos.preset"].create({
            "name": "Fixed 10",
            "service_fee": True,
            "service_fee_type": "fixed",
            "service_fee_amount": 10,
        })
        self.main_pos_config.write({
            "use_presets": True,
            "default_preset_id": preset.id,
            "available_preset_ids": [Command.set([])],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "ServiceFeePromotionTour",
            login="pos_user",
        )
