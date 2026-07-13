# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestPosLoyaltyServiceFee(TestPointOfSaleHttpCommon):
    def setUp(self):
        super().setUp()
        # Only the program each test creates should apply to its order.
        self.env["loyalty.program"].search([]).write({"active": False})
        self.env["product.product"].create({
            "name": "Item",
            "available_in_pos": True,
            "list_price": 50.0,
            "taxes_id": [Command.clear()],
        })

    def _create_preset(self, name, service_fee_type, amount, based_on="pre_discount"):
        return self.env["pos.preset"].create({
            "name": name,
            "service_fee": True,
            "service_fee_type": service_fee_type,
            "service_fee_amount": amount,
            "service_fee_based_on": based_on,
        })

    def _create_discount_on_order_program(self, discount):
        return self.env["loyalty.program"].create({
            "name": "Auto %d%% on order" % discount,
            "program_type": "promotion",
            "trigger": "auto",
            "rule_ids": [Command.create({})],
            "reward_ids": [Command.create({
                "reward_type": "discount",
                "discount": discount,
                "discount_mode": "percent",
                "discount_applicability": "order",
            })],
        })

    def _start_tour(self, tour, default_preset, available_presets=()):
        self.main_pos_config.write({
            "use_presets": True,
            "default_preset_id": default_preset.id,
            "available_preset_ids": [Command.set([preset.id for preset in available_presets])],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, tour, login="pos_user")

    def test_service_fee_single_line_with_a_gift_card(self):
        """
        A gift card is not something the fee is taken from. Its reward line used
        to join that base and add a second fee line to the order.
        """
        # A session only opens on a gift card program that can be printed.
        self.env.ref("loyalty.gift_card_product_50").product_tmpl_id.write({"active": True})
        program = self.env["loyalty.program"].browse(
            self.env["loyalty.program"].create_from_template("gift_card")["res_id"]
        )
        program.pos_report_print_id = self.env.ref("loyalty.report_gift_card")
        self.env["loyalty.card"].create({
            "program_id": program.id,
            "code": "GIFTCARD",
        })._adjust_points(100, "Initial balance")
        self._start_tour(
            "ServiceFeeGiftCardSingleLineTour",
            self._create_preset("Percent 10 before discount", "percent", 0.1),
        )

    def test_service_fee_covered_by_an_ewallet(self):
        """
        An eWallet settles the whole bill, service fee included, and is no part
        of the total the fee is a percentage of — before or after discount.
        """
        ewallet_product = self.env.ref("loyalty.ewallet_product_50")
        ewallet_product.product_tmpl_id.write({"active": True})
        program = self.env["loyalty.program"].create({
            "name": "eWallet Program",
            "program_type": "ewallet",
            "applies_on": "future",
            "trigger": "auto",
            "rule_ids": [Command.create({
                "reward_point_mode": "money",
                "reward_point_amount": 1,
                "product_ids": ewallet_product,
            })],
            "reward_ids": [Command.create({
                "reward_type": "discount",
                "discount_mode": "per_point",
                "discount": 1,
            })],
            "trigger_product_ids": ewallet_product,
        })
        partner = self.env["res.partner"].create({"name": "AAAAAAA"})
        self.env["loyalty.card"].create({
            "program_id": program.id,
            "partner_id": partner.id,
        })._adjust_points(100, "Initial balance")
        self._start_tour(
            "ServiceFeeEWalletCoversFeeTour",
            self._create_preset("Percent 10 before discount", "percent", 0.1),
            [self._create_preset("Percent 10 after discount", "percent", 0.1, "post_discount")],
        )

    def test_service_fee_fixed_scales_under_a_promotion(self):
        """
        The quantity and the price of a fixed fee are the cashier's: a promotion
        recomputing the order must not round them off nor take them back.
        """
        self._create_discount_on_order_program(10)
        self._start_tour(
            "ServiceFeeFixedPromotionScalingTour",
            self._create_preset("Fixed 10", "fixed", 10),
        )

    def test_service_fee_stays_out_of_the_promotion(self):
        """
        A discount on order discounts what was ordered, and the fee is a charge
        on top of it: editing the fee used to move the discount. Only a gift card /
        eWallet reward settles the fee, as it settles the whole bill.
        """
        self._create_discount_on_order_program(10)
        self._start_tour(
            "ServiceFeePromotionExcludesFeeTour",
            self._create_preset("Percent 10 before discount", "percent", 0.1),
        )

    def test_service_fee_recomputed_when_a_reward_is_deactivated(self):
        """
        A fee based on the total after discount includes the reward line in its
        base. Deleting that line emits no event, so the fee used to keep the amount
        the deactivated reward had reduced.
        """
        self._create_discount_on_order_program(10)
        self._start_tour(
            "ServiceFeeRewardDeactivationTour",
            self._create_preset("Percent 10 after discount", "percent", 0.1, "post_discount"),
        )

    def test_service_fee_survives_a_full_discount(self):
        """
        A promotion covering the whole order used to take the fee with it: a fee
        carved out of a base of zero is no fee at all.
        """
        self._create_discount_on_order_program(100)
        self._start_tour(
            "ServiceFeeFullDiscountTour",
            self._create_preset("Fixed 10", "fixed", 10),
            [
                self._create_preset("Percent 10 before discount", "percent", 0.1),
                self._create_preset("Percent 10 after discount", "percent", 0.1, "post_discount"),
            ],
        )
