from odoo import models, fields, api


class EgProductTemplate(models.Model):
    _name = "eg.product.template"
    _rec_name = "odoo_product_tmpl_id"

    odoo_product_tmpl_id = fields.Many2one(comodel_name="product.template", string="Odoo Product", required=True)
    instance_id = fields.Many2one(comodel_name="eg.ecom.instance", string="Instance", required=True)
    provider = fields.Selection(related="instance_id.provider", store=True)
    inst_product_tmpl_id = fields.Char(string="Instance Product")
    update_required = fields.Boolean(string="Update Required")
    product_tmpl_image = fields.Binary(string="Image")
    template_image_ids = fields.One2many(comodel_name="eg.template.image", inverse_name="eg_template_id",
                                         string="Template Images")
    variant_count = fields.Integer(string="Total Variant", compute="compute_on_variant_count")
    eg_product_ids = fields.One2many(comodel_name="eg.product.product", inverse_name="eg_tmpl_id", string="Products")
    _sql_constraints = [
        ('inst_product_tmpl_uniq', 'unique(instance_id, inst_product_tmpl_id)',
         'Combination of instance and inst_product_tmpl_id must be unique!!!'), ]

    # Extra fields for middle layer
    name = fields.Char(string="Name")
    price = fields.Float(string="Sale Price")
    default_code = fields.Char(string="Internal Reference")
    weight = fields.Float(string="Weight")
    barcode = fields.Char(string="Barcode")
    qty_available = fields.Integer(string="Quantity Available")
    eg_attribute_line_ids = fields.One2many(comodel_name="eg.product.attribute.line", inverse_name="eg_product_tmpl_id",
                                            string="Attribute Lines")
    eg_category_id = fields.Many2one(comodel_name="eg.product.category", string="Category")
    description = fields.Text(string="Description")
    eg_category_ids = fields.Many2many(comodel_name="eg.product.category", string="Categories")

    # Add new by akash
    sale_count = fields.Integer("Sale Count")

    def compute_on_variant_count(self):
        for rec in self:
            if rec.eg_product_ids:
                rec.variant_count = len(rec.eg_product_ids)
