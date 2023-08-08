# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route

from odoo.addons.sale_product_configurator.controllers.main import ProductConfiguratorController


class WebsiteSaleProductConfiguratorController(ProductConfiguratorController):

    @route(auth='public')
    def get_product_configurator_values(self, *args, **kwargs):
        # TODO VCR: remove furniture ?
        return super().get_product_configurator_values(*args, **kwargs)

    @route(auth='public')
    def sale_product_configurator_create_product(self, *args, **kwargs):
        return super().sale_product_configurator_create_product(*args, **kwargs)  # TODO VCR : sudo ?

    @route(auth='public')
    def sale_product_configurator_update_combination(self, *args, **kwargs):
        return super().sale_product_configurator_update_combination(*args, **kwargs)

    @route(auth='public')
    def sale_product_configurator_get_optional_products(self, *args, **kwargs):
        return super().sale_product_configurator_get_optional_products(*args, **kwargs)
