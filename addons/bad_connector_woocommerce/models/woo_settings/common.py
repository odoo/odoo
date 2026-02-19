import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class WooSettings(models.Model):
    _name = "woo.settings"
    _description = "WooCommerce Settings"
    _inherit = "woo.binding"

    name = fields.Char(required=True)
    woo_type = fields.Char()
    default = fields.Char()
    value = fields.Char()
    odoo_id = fields.Many2one(
        string="WooCommerce Settings", comodel_name="woo.settings"
    )
    stock_update = fields.Boolean()


class WooSettingsAdapter(Component):
    """Adapter for WooCommerce Settings"""

    _name = "woo.setting.adapter"
    _inherit = "woo.adapter"
    _apply_on = "woo.settings"
    _woo_model = "settings/tax"
    _woo_product_stock = "settings/products/woocommerce_manage_stock"
    _woo_default_currency = "settings/general/woocommerce_currency"
    _woo_default_weight = "settings/products/woocommerce_weight_unit"
    _woo_default_dimension = "settings/products/woocommerce_dimension_unit"
    _woo_ext_id_key = "id"

    def search(self, filters=None, **kwargs):
        """Inherited search method to pass different API
        to fetch additional data"""
        kwargs["_woo_product_stock"] = self._woo_product_stock
        kwargs["_woo_default_currency"] = self._woo_default_currency
        kwargs["_woo_default_weight"] = self._woo_default_weight
        kwargs["_woo_default_dimension"] = self._woo_default_dimension

        return super(WooSettingsAdapter, self).search(filters, **kwargs)
