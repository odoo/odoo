import logging

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    woo_bind_ids = fields.One2many(
        comodel_name="woo.product.attribute",
        inverse_name="odoo_id",
        string="WooCommerce Bindings",
        copy=False,
    )
    has_archives = fields.Boolean()
    not_real = fields.Boolean()

    def import_product_attribute_value(self):
        """Import Product Attribute Value"""
        for binding in self.woo_bind_ids:
            binding.sync_attribute_values_from_woo()


class WooProductAttribute(models.Model):
    """Woocommerce product attribute"""

    _name = "woo.product.attribute"
    _inherit = "woo.binding"
    _inherits = {"product.attribute": "odoo_id"}
    _description = "WooCommerce Product Attribute"
    _rec_name = "name"

    odoo_id = fields.Many2one(
        comodel_name="product.attribute",
        string="Product Attribute",
        required=True,
        ondelete="restrict",
    )

    def sync_attribute_values_from_woo(self):
        """sync Attribute values from woocommerce"""
        self.ensure_one()
        filters = {}
        if not self.backend_id:
            raise ValidationError(_("No Backend found on Product Attribute."))
        if not self.external_id:
            raise ValidationError(_("No External Id found in backend"))
        filters.update(
            {
                "attribute": self.external_id,
            }
        )
        # TODO: with_delay only if context has delay key passed from after import. Else
        # it should be without delay
        self.backend_id._sync_from_date(
            model="woo.product.attribute.value",
            priority=5,
            filters=filters,
        )


class WooProductAttributeAdapter(Component):
    """Adapter for WooCommerce Product Attribute"""

    _name = "woo.product.attribute.adapter"
    _inherit = "woo.adapter"
    _apply_on = "woo.product.attribute"
    _woo_model = "products/attributes"
    _woo_ext_id_key = "id"
