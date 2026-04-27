# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.sale.controllers.combo_configurator import SaleComboConfiguratorController
from odoo.addons.sale_renting.controllers.utils import _convert_rental_dates


class SaleRentingComboConfiguratorController(SaleComboConfiguratorController):

    @route()
    def sale_combo_configurator_get_data(self, *args, **kwargs):
        _convert_rental_dates(kwargs)
        return super().sale_combo_configurator_get_data(*args, **kwargs)

    @route()
    def sale_combo_configurator_get_price(self, *args, **kwargs):
        _convert_rental_dates(kwargs)
        return super().sale_combo_configurator_get_price(*args, **kwargs)
