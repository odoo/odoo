# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.sale.controllers.combo_configurator import (
    SaleComboConfiguratorController,
)
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleComboConfiguratorController(SaleComboConfiguratorController, WebsiteSale):

    @route(
        route='/website_sale/combo_configurator/get_data',
        type='jsonrpc',
        auth='public',
        website=True,
        readonly=True,
    )
    def website_sale_combo_configurator_get_data(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        return super().sale_combo_configurator_get_data(*args, **kwargs)

    @route(
        route='/website_sale/combo_configurator/get_price',
        type='jsonrpc',
        auth='public',
        website=True,
        readonly=True,
    )
    def website_sale_combo_configurator_get_price(self, *args, **kwargs):
        self._populate_currency_and_pricelist(kwargs)
        return super().sale_combo_configurator_get_price(*args, **kwargs)
