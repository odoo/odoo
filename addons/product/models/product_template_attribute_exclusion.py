# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplateAttributeExclusion(models.Model):
    _name = 'product.template.attribute.exclusion'
    _description = "Product Template Attribute Exclusion"
    _order = 'product_tmpl_id, id'

    product_template_attribute_value_id = fields.Many2one(
        comodel_name='product.template.attribute.value',
        string="Attribute Value",
        ondelete='cascade',
        index=True)
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string="Product Template",
        ondelete='cascade',
        required=True,
        index=True)
    value_ids = fields.Many2many(
        comodel_name='product.template.attribute.value',
        relation='product_attr_exclusion_value_ids_rel',
        string="Attribute Values",
        domain="[('product_tmpl_id', '=', product_tmpl_id), ('ptav_active', '=', True)]")

    @api.model_create_multi
    def create(self, vals_list):
        exclusions = super().create(vals_list)
        exclusions.product_tmpl_id._create_variant_ids()
        return exclusions

    def unlink(self):
        # Keep a reference to the related templates before the deletion.
        templates = self.product_tmpl_id
        res = super().unlink()
        templates._create_variant_ids()
        return res

    def write(self, vals):
        templates = self.env['product.template']
        if 'product_tmpl_id' in vals:
            templates = self.product_tmpl_id
        res = super().write(vals)
        (templates | self.product_tmpl_id)._create_variant_ids()
        return res
