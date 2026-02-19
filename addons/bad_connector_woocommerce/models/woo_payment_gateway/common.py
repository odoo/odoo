import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class WooPaymentGateway(models.Model):
    _name = "woo.payment.gateway"
    _description = "WooCommerce Payment Gateway"
    _inherit = "woo.binding"

    name = fields.Char(required=True)
    slug = fields.Char()
    enable = fields.Boolean()
    description = fields.Text()
    workflow_process_id = fields.Many2one(comodel_name="sale.workflow.process")


class WooPaymentGatewayAdapter(Component):
    """Adapter for WooCommerce Payment Gateway"""

    _name = "woo.payment.gateway.adapter"
    _inherit = "woo.adapter"
    _apply_on = "woo.payment.gateway"
    _woo_model = "payment_gateways"
    _woo_ext_id_key = "id"
