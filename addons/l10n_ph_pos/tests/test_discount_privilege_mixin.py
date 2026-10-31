# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegeMixin(TestPhCommon):
    """
    Low-level coverage of the l10n_ph.discount.privilege.line.mixin hooks as
    ported onto pos.order.line, ahead of the splitting engine/wizard that
    will drive them from the POS UI.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("point_of_sale.group_pos_manager")

        ChartTemplate = cls.env["account.chart.template"].with_company(
            cls.company_data["company"],
        )
        cls.tax_sale_12 = ChartTemplate.ref("l10n_ph_tax_sale_12")

        cls.product = cls.env["product.product"].create(
            {
                "name": "Pizza Margherita",
                "list_price": 1000.0,
                "taxes_id": [Command.set(cls.tax_sale_12.ids)],
                "property_account_income_id": cls.company_data["default_account_revenue"].id,
            },
        )
        cls.pos_config = cls.env["pos.config"].create(
            {
                "name": "Test Restaurant",
                "company_id": cls.company_data["company"].id,
            },
        )
        cls.pos_session = cls.env["pos.session"].create(
            {
                "config_id": cls.pos_config.id,
                "user_id": cls.env.uid,
            },
        )

    def _create_order_line(self, qty=1.0, price_unit=None):
        price_unit = self.product.list_price if price_unit is None else price_unit
        order = self.env["pos.order"].create(
            {
                "name": "Test Order",
                "company_id": self.company_data["company"].id,
                "session_id": self.pos_session.id,
                "amount_tax": 0.0,
                "amount_total": 0.0,
                "amount_paid": 0.0,
                "amount_return": 0.0,
                "lines": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "qty": qty,
                            "price_unit": price_unit,
                            "tax_ids": [Command.set(self.tax_sale_12.ids)],
                            "price_subtotal": 0.0,
                            "price_subtotal_incl": 0.0,
                        },
                    ),
                ],
            },
        )
        order.lines._onchange_amount_line_all()
        return order.lines

    def test_gross_price_details_ignore_discount(self):
        """The gross recompute must ignore any discount already on the line."""
        line = self._create_order_line(qty=2.0)
        line.discount = 50.0
        gross_subtotal, subtotal_discount, gross_total, total_discount = (
            line._l10n_ph_get_discount_price_details()
        )
        self.assertAlmostEqual(gross_subtotal, 2000.0, places=2)
        self.assertAlmostEqual(gross_total, 2240.0, places=2)
        # No privilege applied yet: the line's own price_subtotal/incl were
        # computed without a discount, so the gross recompute matches them.
        self.assertAlmostEqual(subtotal_discount, 0.0, places=2)
        self.assertAlmostEqual(total_discount, 0.0, places=2)

    def test_skip_discount_amounts_on_combo_line(self):
        combo_item_product = self.env["product.product"].create(
            {"name": "Combo Item", "list_price": 0.0},
        )
        combo = self.env["product.combo"].create(
            {
                "name": "Combo Choice",
                "combo_item_ids": [Command.create({"product_id": combo_item_product.id})],
            },
        )
        combo_product = self.env["product.product"].create(
            {"name": "Combo", "type": "combo", "combo_ids": [Command.set(combo.ids)]},
        )
        order = self.env["pos.order"].create(
            {
                "name": "Combo Order",
                "company_id": self.company_data["company"].id,
                "session_id": self.pos_session.id,
                "amount_tax": 0.0,
                "amount_total": 0.0,
                "amount_paid": 0.0,
                "amount_return": 0.0,
                "lines": [
                    Command.create(
                        {
                            "product_id": combo_product.id,
                            "qty": 1.0,
                            "price_unit": 0.0,
                            "price_subtotal": 0.0,
                            "price_subtotal_incl": 0.0,
                        },
                    ),
                ],
            },
        )
        self.assertTrue(order.lines._l10n_ph_skip_discount_amounts())
        self.assertRecordValues(order.lines, [{
            "l10n_ph_special_discount_amount": 0.0,
            "l10n_ph_regular_discount_amount": 0.0,
        }])
