import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class ProductTag(models.Model):
    """Product Tag"""

    _inherit = "product.tag"

    woo_bind_ids = fields.One2many(
        comodel_name="woo.product.tag",
        inverse_name="odoo_id",
        string="WooCommerce Bindings",
        copy=False,
    )


class WooProductTag(models.Model):
    """Woocommerce product tag"""

    _name = "woo.product.tag"
    _inherit = "woo.binding"
    _inherits = {"product.tag": "odoo_id"}
    _description = "WooCommerce Product Tag"

    _rec_name = "name"

    odoo_id = fields.Many2one(
        comodel_name="product.tag",
        string="Product Tag",
        required=True,
        ondelete="restrict",
    )

    slug = fields.Char()
    description = fields.Text()


class WooProductTagAdapter(Component):
    """Adapter for WooCommerce Product Tag"""

    _name = "woo.product.tag.adapter"
    _inherit = "woo.adapter"
    _apply_on = "woo.product.tag"
    _woo_model = "products/tags"
    _woo_ext_id_key = "id"
