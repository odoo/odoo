# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.l10n_ph_pos.tests.common import TestPosDiscountPrivilegeHttpCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegesLoyaltyFrontend(TestPosDiscountPrivilegeHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["loyalty.program"].search([]).write({"active": False})
        cls.env["loyalty.program"].create({
            "name": "Order Promotion",
            "program_type": "promotion",
            "trigger": "auto",
            "applies_on": "current",
            "rule_ids": [(0, 0, {})],
            "reward_ids": [(0, 0, {
                "reward_type": "discount",
                "discount": 10,
                "discount_mode": "percent",
                "discount_applicability": "order",
                "description": "10% on the order",
            })],
        })

    def test_loyalty_discount_skips_privileged_lines(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_ph_pos_loyalty_discount_privileges")
