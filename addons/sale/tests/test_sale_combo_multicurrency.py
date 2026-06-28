# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged("post_install", "-at_install")
class TestSaleComboMultiCurrency(SaleCommon):
    @freeze_time("2026-01-01")
    def test_combo_item_extra_price_currency_conversion(self):
        """Combo item extra_price must be converted to the order currency."""
        # 1 USD = 1000 ARS
        ars = self.setup_other_currency("ARS", rates=[("2026-01-01", 1000.0)])
        pricelist_ars = self._create_pricelist(currency_id=ars.id)

        product = self._create_product(name="Veterinary Kit", list_price=1200.0)
        combo = self.env["product.combo"].create({
            "name": "Vet Combo",
            "combo_item_ids": [Command.create({"product_id": product.id, "extra_price": 1700.0})],
        })
        combo_product = self._create_product(
            name="Combo K1EX10-VET",
            list_price=200.0,
            type="combo",
            combo_ids=[Command.link(combo.id)],
        )
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "pricelist_id": pricelist_ars.id,
            "date_order": "2026-01-01 00:00:00",
        })
        parent_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": combo_product.id,
            "product_uom_qty": 1,
        })
        combo_item = combo.combo_item_ids[0]
        child_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.id,
            "combo_item_id": combo_item.id,
            "linked_line_id": parent_line.id,
            "product_uom_qty": 1,
        })

        # combo base 200 USD → 200,000 ARS; extra 1700 USD → 1,700,000 ARS
        self.assertAlmostEqual(
            child_line._get_combo_item_display_price(), 200.0 * 1000.0 + 1700.0 * 1000.0, places=2
        )

    @freeze_time("2026-01-01")
    def test_combo_item_extra_price_same_currency(self):
        """No conversion when pricelist currency matches the company currency."""
        pricelist_usd = self._create_pricelist(currency_id=self.env.company.currency_id.id)
        product = self._create_product(name="Product USD", list_price=1200.0)
        combo = self.env["product.combo"].create({
            "name": "Combo USD",
            "combo_item_ids": [Command.create({"product_id": product.id, "extra_price": 1700.0})],
        })
        combo_product = self._create_product(
            name="Combo product USD",
            list_price=200.0,
            type="combo",
            combo_ids=[Command.link(combo.id)],
        )
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "pricelist_id": pricelist_usd.id,
            "date_order": "2026-01-01 00:00:00",
        })
        parent_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": combo_product.id,
            "product_uom_qty": 1,
        })
        combo_item = combo.combo_item_ids[0]
        child_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.id,
            "combo_item_id": combo_item.id,
            "linked_line_id": parent_line.id,
            "product_uom_qty": 1,
        })

        self.assertAlmostEqual(child_line._get_combo_item_display_price(), 200.0 + 1700.0, places=2)
