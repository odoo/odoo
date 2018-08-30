# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class ProductAttribute(models.Model):
    _name = "product.attribute"
    _description = "Product Attribute"
    _order = 'sequence, name'

    name = fields.Char('Attribute', required=True, translate=True)
    value_ids = fields.One2many('product.attribute.value', 'attribute_id', 'Values', copy=True)
    sequence = fields.Integer('Sequence', help="Determine the display order")
    attribute_line_ids = fields.One2many('product.attribute.line', 'attribute_id', 'Lines')
    create_variant = fields.Boolean(default=True, help="Check this if you want to create multiple variants for this attribute.")


class ProductAttributeValue(models.Model):
    _name = "product.attribute.value"
    _order = 'attribute_id, sequence, id'
    _description = 'Product Attribute Value'

    name = fields.Char(string='Value', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', help="Determine the display order")
    attribute_id = fields.Many2one('product.attribute', string='Attribute', ondelete='cascade', required=True)

    _sql_constraints = [
        ('value_company_uniq', 'unique (name, attribute_id)', 'This attribute value already exists !')
    ]

    @api.multi
    def name_get(self):
        if not self._context.get('show_attribute', True):  # TDE FIXME: not used
            return super(ProductAttributeValue, self).name_get()
        return [(value.id, "%s: %s" % (value.attribute_id.name, value.name)) for value in self]

    @api.multi
    def _variant_name(self, variable_attributes):
        return ", ".join([v.name for v in self if v.attribute_id in variable_attributes])

    @api.multi
    def unlink(self):
        linked_products = self.env['product.product'].with_context(active_test=False).search([('attribute_value_ids', 'in', self.ids)])
        if linked_products:
            raise UserError(_('The operation cannot be completed:\nYou are trying to delete an attribute value with a reference on a product variant.'))
        return super(ProductAttributeValue, self).unlink()


class ProductProductAttributeValue(models.Model):
    _name = "product.product.attribute.value"

    name = fields.Char('Value', related="product_attribute_value_id.name")
    product_attribute_value_id = fields.Many2one('product.attribute.value', string='Attribute Value', required=True, ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True, ondelete='cascade', index=True)
    attribute_id = fields.Many2one('product.attribute', string='Attribute', related="product_attribute_value_id.attribute_id")
    sequence = fields.Integer('product.sequence', related="product_attribute_value_id.sequence")
    price_extra = fields.Float(
        string='Attribute Price Extra', default=0.0, digits=dp.get_precision('Product Price'),
        help="Price Extra: Extra price for the variant with this attribute value on sale price. eg. 200 price extra, 1000 + 200 = 1200.")
    exclude_for = fields.Many2many(
        'product.attribute.filter.line', string="Exclude for", relation="product_attribute_value_exclusion",
        help="""A list of product and attribute values that you want to exclude for this product's attribue value.
        Also applies on optionnal and accessory products.""")

    @api.multi
    def name_get(self):
        if not self._context.get('show_attribute', True):  # TDE FIXME: not used
            return super(ProductAttributeValue, self).name_get()
        return [(value.id, "%s: %s" % (value.attribute_id.name, value.name)) for value in self]


class ProductAttributeFilterLine(models.Model):
    _name = "product.attribute.filter.line"

    product_tmpl_id = fields.Many2one('product.template', string='Product Template', ondelete='cascade', required=True)
    value_ids = fields.Many2many(
        'product.product.attribute.value', relation="product_attr_filter_line_value_ids_rel",
        string='Attribute Values', domain="[('product_tmpl_id', '=', product_tmpl_id), ('attribute_id.create_variant', '=', True)]")


class ProductAttributeLine(models.Model):
    _name = "product.attribute.line"
    _rec_name = 'attribute_id'
    _description = 'Product Attribute Line'

    product_tmpl_id = fields.Many2one('product.template', string='Product Template', ondelete='cascade', required=True)
    attribute_id = fields.Many2one('product.attribute', string='Attribute', ondelete='restrict', required=True)
    value_ids = fields.Many2many('product.attribute.value', string='Attribute Values')
    product_value_ids = fields.Many2many('product.product.attribute.value', string='Product Attribute Values', compute="_set_product_value_ids")

    @api.constrains('value_ids', 'attribute_id')
    def _check_valid_attribute(self):
        if any(line.value_ids > line.attribute_id.value_ids for line in self):
            raise ValidationError(_('You cannot use this attribute with the following value.'))
        return True

    @api.model
    def create(self, values):
        res = super(ProductAttributeLine, self).create(values)
        res._update_product_product_attribute_values()
        return res

    def write(self, values):
        res = super(ProductAttributeLine, self).write(values)
        self._update_product_product_attribute_values()
        return res

    @api.depends('value_ids')
    def _set_product_value_ids(self):
        for product_attribute_line in self:
            product_attribute_line.product_value_ids = self.env['product.product.attribute.value'].search([
                ('product_tmpl_id', 'in', product_attribute_line.product_tmpl_id.ids),
                ('product_attribute_value_id.attribute_id', 'in', product_attribute_line.value_ids.mapped('attribute_id').ids)])

    @api.multi
    def unlink(self):
        for product_attribute_line in self:
            self.env['product.product.attribute.value'].search([
                ('product_tmpl_id', 'in', product_attribute_line.product_tmpl_id.ids), 
                ('product_attribute_value_id.attribute_id', 'in', product_attribute_line.value_ids.mapped('attribute_id').ids)]).unlink()

        return super(ProductAttributeLine, self).unlink()

    def _update_product_product_attribute_values(self):
        """
        Create or unlink product.product.attribute.value based on the attribute lines.
        If the product.attribute.value is removed, remove the corresponding product.product.attribute.value
        If no product.product.attribute.value exists for the newly added product.attribute.value, create it.
        """
        for attribute_line in self:
            # All existing product.product.attribute.value for this template
            product_product_attribute_values_to_remove = self.env['product.product.attribute.value'].search([
                ('product_tmpl_id', '=', attribute_line.product_tmpl_id.id),
                ('product_attribute_value_id.attribute_id', 'in', attribute_line.value_ids.mapped('attribute_id').ids)])
            # All existing product.attribute.value shared by all products
            # eg (Yellow, Red, Blue, Small, Large)
            existing_product_attribute_values = product_product_attribute_values_to_remove.mapped('product_attribute_value_id')

            # Loop on product.attribute.values for the line (eg: Yellow, Red, Blue)
            for product_attribute_value in attribute_line.value_ids:
                if product_attribute_value in existing_product_attribute_values:
                    # property is already existing: don't touch, remove it from list to avoid unlinking it
                    product_product_attribute_values_to_remove = product_product_attribute_values_to_remove.filtered(
                        lambda value: product_attribute_value not in value.mapped('product_attribute_value_id')
                    )
                else:
                    # property does not exist: create it
                    self.env['product.product.attribute.value'].create({
                        'product_attribute_value_id': product_attribute_value.id,
                        'product_tmpl_id': attribute_line.product_tmpl_id.id})
            # at this point, existing properties can be removed to reflect the modifications on value_ids
            if product_product_attribute_values_to_remove:
                product_product_attribute_values_to_remove.unlink()

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            args = expression.AND([['|', ('attribute_id', operator, name), ('value_ids', operator, name)], args])
            attribute_ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
            return self.browse(attribute_ids).name_get()
        return super(ProductAttributeLine, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
