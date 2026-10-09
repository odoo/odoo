# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegesGlobalDiscountFrontend(TestPointOfSaleHttpCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ph")
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.write({
            "module_pos_discount": True,
            "discount_product_id": cls.env["product.product"].create({
                "name": "Global Discount",
                "type": "service",
                "available_in_pos": True,
            }).id,
        })
        cls.juan = cls.env["res.partner"].create({
            "name": "Juan Dela Cruz",
            "country_id": cls.env.ref("base.ph").id,
            "additional_identifiers": {"PH_SC_ID": "SC-REG-001"},
        })
        tax_sale_12 = cls.env["account.chart.template"].with_company(cls.env.company).ref("l10n_ph_tax_sale_12")
        cls.soda = cls.env["product.template"].create({
            "name": "Test Soda",
            "available_in_pos": True,
            "list_price": 100.0,
            "taxes_id": [(6, 0, tax_sale_12.ids)],
        })

    def test_global_discount_skips_privileged_lines(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_ph_pos_discount_discount_privileges")

        order = self.env["pos.order"].search([("session_id", "=", self.main_pos_config.current_session_id.id)])
        self.assertEqual(order.state, "paid")
        discount_line = order.lines.filtered(lambda line: line.product_id == self.main_pos_config.discount_product_id)
        self.assertAlmostEqual(discount_line.price_subtotal_incl, -11.2, places=2)
        self.assertAlmostEqual(order.amount_total, 180.8, places=2)
