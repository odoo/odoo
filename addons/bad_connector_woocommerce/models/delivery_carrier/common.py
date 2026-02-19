from odoo import fields, models

from odoo.addons.component.core import Component


class DeliveryCarrier(models.Model):
    """Delivery Carrier"""

    _inherit = "delivery.carrier"

    woo_bind_ids = fields.One2many(
        comodel_name="woo.delivery.carrier",
        inverse_name="odoo_id",
        string="WooCommerce Bindings",
        copy=False,
    )


class WooDeliveryCarrier(models.Model):
    """Woocommerce Delivery Carrier"""

    _name = "woo.delivery.carrier"
    _inherit = "woo.binding"
    _inherits = {"delivery.carrier": "odoo_id"}
    _description = "WooCommerce Delivery Carrier"

    odoo_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Delivery Carrier",
        required=True,
        ondelete="restrict",
    )

    title = fields.Char()
    description = fields.Text()


class WooDeliveryCarrierAdapter(Component):
    """Adapter for Woocommerce Delivery Carrier"""

    _name = "woo.delivery.carrier.adapter"
    _inherit = "woo.adapter"
    _apply_on = "woo.delivery.carrier"

    _woo_model = "shipping_methods"
    _woo_key = "id"
    _woo_ext_id_key = "id"
