# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegesLoyaltyFrontend(TestPointOfSaleHttpCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ph")
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
        cls.env["res.partner"].create({
            "name": "Juan Dela Cruz",
            "country_id": cls.env.ref("base.ph").id,
            "additional_identifiers": {"PH_SC_ID": "SC-REG-001"},
        })
        tax_sale_12 = cls.env["account.chart.template"].with_company(cls.env.company).ref("l10n_ph_tax_sale_12")
        cls.env["product.template"].create({
            "name": "Test Soda",
            "available_in_pos": True,
            "list_price": 100.0,
            "taxes_id": [(6, 0, tax_sale_12.ids)],
        })

    def test_loyalty_discount_skips_privileged_lines(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_ph_pos_loyalty_discount_privileges")
