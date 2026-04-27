# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.sale_renting.controllers.combo_configurator import (
    SaleRentingComboConfiguratorController,
)
from odoo.addons.sale_renting.controllers.utils import _convert_rental_dates
from odoo.addons.website_sale.controllers.combo_configurator import (
    WebsiteSaleComboConfiguratorController,
)


class WebsiteSaleRentingComboConfiguratorController(
    WebsiteSaleComboConfiguratorController, SaleRentingComboConfiguratorController
):

    @route()
    def website_sale_combo_configurator_get_data(self, *args, **kwargs):
        _convert_rental_dates(kwargs)
        return super().website_sale_combo_configurator_get_data(*args, **kwargs)

    @route()
    def website_sale_combo_configurator_get_price(self, *args, **kwargs):
        _convert_rental_dates(kwargs)
        return super().website_sale_combo_configurator_get_price(*args, **kwargs)

    @route()
    def website_sale_combo_configurator_update_cart(self, *args, **kwargs):
        _convert_rental_dates(kwargs)
        return super().website_sale_combo_configurator_update_cart(*args, **kwargs)
