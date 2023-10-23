# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductAttributeCustomValue(models.Model):
    _name = 'product.attribute.custom.value'
    _description = "Product Attribute Custom Value"
    _order = 'custom_product_template_attribute_value_id, id'

    name = fields.Char(string="Name", compute='_compute_name')
    custom_product_template_attribute_value_id = fields.Many2one(
        comodel_name='product.template.attribute.value',
        string="Attribute Value",
        required=True,
        ondelete='restrict')
    custom_value = fields.Char(string="Custom Value")
    res_id = fields.Many2oneReference('Resource ID', model_field='res_model', readonly=True)
    res_model = fields.Char('Resource Model', readonly=True)

    @api.depends('custom_product_template_attribute_value_id.name', 'custom_value')
    def _compute_name(self):
        for record in self:
            name = (record.custom_value or '').strip()
            if record.custom_product_template_attribute_value_id.display_name:
                name = "%s: %s" % (record.custom_product_template_attribute_value_id.display_name, name)
            record.name = name

    _sql_constraints = [
        ('custom_value_unique', 'unique(custom_product_template_attribute_value_id, res_id, res_model)',
        "Only one Custom Value is allowed per Attribute Value per Model implementing the Product Description Mixin.")
    ]
