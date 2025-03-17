# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.payment_custom.tests.common import PaymentCustomCommon
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


class ClickAndCollectCommon(PaymentCustomCommon, WebsiteSaleStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.storable_product = cls._create_product()
        cls._add_product_qty_to_wh(cls.storable_product.id, 10, cls.warehouse.lot_stock_id.id)

        # Create the in-store delivery method.
        cls.dm_product = cls._prepare_carrier_product(list_price=0.0)
        cls.provider = cls._prepare_provider(code='custom', custom_mode='on_site')
        cls.in_store_dm = cls._prepare_carrier(
            cls.dm_product,
            fixed_price=0.0,
            delivery_type='in_store',
            warehouse_ids=[Command.set([cls.warehouse.id])],
            name="Example in-store delivery",
            is_published=True,
        )

    def _create_in_store_delivery_order(self, **values):
        default_values = {
            'partner_id': self.partner.id,
            'website_id': self.website.id,
            'order_line': [Command.create({
                'product_id': self.storable_product.id,
                'product_uom_qty': 5.0,
            })],
            'carrier_id': self.in_store_dm.id,
        }
        return self.env['sale.order'].create(dict(default_values, **values))
