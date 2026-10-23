import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class WooTax(models.Model):
    _name = "woo.tax"
    _inherit = "woo.binding"
    _description = "WooCommerce Taxes"

    name = fields.Char(required=True)
    woo_amount = fields.Float()
    woo_rate = fields.Char()
    woo_tax_name = fields.Char(string="WooCommerce Tax Name")
    priority = fields.Char()
    shipping = fields.Char()
    woo_class = fields.Char()
    compound = fields.Char()
    state = fields.Char()
    city = fields.Char()
    country = fields.Char()
    cities = fields.Char()
    postcode = fields.Char()
    postcodes = fields.Char()
    woo_bind_ids = fields.One2many(
        comodel_name="woo.tax",
        inverse_name="odoo_id",
        string="WooCommerce Bindings",
        copy=False,
    )
    odoo_id = fields.Many2one(string="Taxes", comodel_name="account.tax")


class WooTaxAdapter(Component):
    """Adapter for WooCommerce Tax"""

    _name = "woo.tax.adapter"
    _inherit = "woo.adapter"
    _apply_on = "woo.tax"
    _woo_model = "taxes"
    _woo_ext_id_key = "id"
