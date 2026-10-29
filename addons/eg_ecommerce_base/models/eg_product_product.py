from odoo import models, fields, api


class EgProductProduct(models.Model):
    _name = "eg.product.product"
    _rec_name = "odoo_product_id"

    odoo_product_id = fields.Many2one(comodel_name="product.product", string="Odoo Product Variant")
    odoo_product_tmpl_id = fields.Many2one(related="odoo_product_id.product_tmpl_id", string="Odoo Product Tmpl",
                                           readonly=True)
    instance_id = fields.Many2one(comodel_name="eg.ecom.instance", string="Instance", required=True)
    provider = fields.Selection(related="instance_id.provider", store=True)
    inst_product_id = fields.Char(string="Instance Product Variant")
    update_required = fields.Boolean(string="Update Required")
    product_image = fields.Binary(string="Image")
    eg_tmpl_id = fields.Many2one(comodel_name="eg.product.template", string="Product Tmpl", ondelete='cascade')
    inst_inventory_item_id = fields.Char(string="Instance Inventory Item Id")
    inst_product_image_id = fields.Char(string="Instance Image ID")
    _sql_constraints = [
        ('inst_product_uniq', 'unique(instance_id, inst_product_id)',
         'Combination of instance and inst_product_id must be unique!!!'),
    ]

    # Extra fields for middle layer
    name = fields.Char(string="Name")
    price = fields.Float(string="Sale Price")
    default_code = fields.Char(string="Internal Reference")
    weight = fields.Float(string="Weight")
    barcode = fields.Char(string="Barcode")
    qty_available = fields.Integer(string="Quantity Available")
    eg_value_ids = fields.Many2many(comodel_name="eg.attribute.value", string="Attribute Value")
    eg_category_id = fields.Many2one(comodel_name="eg.product.category", string="Category")

    # add by akash
    product_price = fields.Float(string="Product Price")
    eg_category_ids = fields.Many2many(comodel_name="eg.product.category", string="Categories")
