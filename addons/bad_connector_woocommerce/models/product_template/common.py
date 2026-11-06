import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    woo_bind_ids = fields.One2many(
        comodel_name="woo.product.template",
        inverse_name="odoo_id",
        string="WooCommerce Bindings",
        copy=False,
    )

    variant_different = fields.Boolean()
    default_code = fields.Char(compute=False, inverse=False)


class WooProductTemplate(models.Model):
    """Woocommerce Product Template"""

    _name = "woo.product.template"
    _inherit = "woo.binding"
    _inherits = {"product.template": "odoo_id"}
    _description = "WooCommerce Product Template"
    _rec_name = "name"

    odoo_id = fields.Many2one(
        comodel_name="product.template",
        string="Odoo Product Template",
        required=True,
        ondelete="restrict",
    )
    woo_product_categ_ids = fields.Many2many(
        comodel_name="woo.product.category",
        string="WooCommerce Product Category(Product)",
        ondelete="restrict",
    )
    woo_attribute_ids = fields.Many2many(
        comodel_name="woo.product.attribute",
        string="WooCommerce Product Attribute",
        ondelete="restrict",
    )
    woo_product_attribute_value_ids = fields.Many2many(
        comodel_name="woo.product.attribute.value",
        string="WooCommerce Product Attribute Value",
        ondelete="restrict",
    )


class WooProductTemplateAdapter(Component):
    """Adapter for WooCommerce Product Template"""

    _name = "woo.product.template.adapter"
    _inherit = "woo.adapter"
    _apply_on = "woo.product.template"
    _woo_model = "products"
    _woo_ext_id_key = "id"
    _check_import_sync_date = True
    _model_dependencies = {
        (
            "woo.product.category",
            "categories",
        ),
        (
            "woo.product.attribute",
            "attributes",
        ),
        (
            "woo.product.tag",
            "tags",
        ),
    }
