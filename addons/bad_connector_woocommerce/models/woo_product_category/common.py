import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class WooProductCategory(models.Model):
    _name = "woo.product.category"
    _description = "WooCommerce Product Category"
    _inherit = "woo.binding"
    _parent_name = "parent_id"
    _parent_store = True

    name = fields.Char(required=True)
    slug = fields.Char()
    display = fields.Char()
    menu_order = fields.Integer()
    count = fields.Integer(readonly=True)
    parent_path = fields.Char(index=True, unaccent=False)
    parent_id = fields.Many2one(
        comodel_name="woo.product.category",
        string="Parent Category",
        index=True,
        ondelete="cascade",
    )
    description = fields.Html(string="Description", translate=True)
    odoo_id = fields.Many2one(
        string="Product Category", comodel_name="product.category"
    )
    woo_child_ids = fields.One2many(
        comodel_name="woo.product.category",
        inverse_name="parent_id",
        string="WooCommerce Child Categories",
    )


class WooProductCategoryAdapter(Component):
    """Adapter for WooCommerce Product Category"""

    _name = "woo.product.category.adapter"
    _inherit = "woo.adapter"
    _apply_on = "woo.product.category"
    _woo_model = "products/categories"
    _woo_ext_id_key = "id"
    _model_dependencies = {
        (
            "woo.product.category",
            "parent",
        )
    }
