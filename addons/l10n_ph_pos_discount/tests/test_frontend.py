# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.l10n_ph_pos.tests.common import TestPosDiscountPrivilegeHttpCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegesGlobalDiscountFrontend(TestPosDiscountPrivilegeHttpCommon):

    @classmethod
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

    def test_global_discount_skips_privileged_lines(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_ph_pos_discount_discount_privileges")

        order = self.env["pos.order"].search([("session_id", "=", self.main_pos_config.current_session_id.id)])
        self.assertRecordValues(order, [{"state": "paid", "amount_total": 180.8}])
        discount_line = order.lines.filtered(lambda line: line.product_id == self.main_pos_config.discount_product_id)
        self.assertRecordValues(discount_line, [{"price_subtotal_incl": -11.2}])
