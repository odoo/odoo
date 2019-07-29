# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class ProductAttribute(models.Model):
    _name = "product.attribute"
    _description = "Product Attribute"
    # if you change this _order, keep it in sync with the method
    # `_sort_key_attribute_value` in `product.template`
    _order = 'sequence, id'

    name = fields.Char('Attribute', required=True, translate=True)
    value_ids = fields.One2many('product.attribute.value', 'attribute_id', 'Values', copy=True)
    sequence = fields.Integer('Sequence', help="Determine the display order", index=True)
    attribute_line_ids = fields.One2many('product.template.attribute.line', 'attribute_id', 'Lines')
    create_variant = fields.Selection([
        ('no_variant', 'Never'),
        ('always', 'Always'),
        ('dynamic', 'Only when the product is added to a sales order')],
        default='always',
        string="Create Variants",
        help="Check this if you want to create multiple variants for this attribute.", required=True)

    def _without_no_variant_attributes(self):
        return self.filtered(lambda pa: pa.create_variant != 'no_variant')

    def write(self, vals):
        """Override to make sure attribute type can't be changed if it's used on
        a product template.

        This is important to prevent because changing the type would make
        existing combinations invalid without recomputing them, and recomputing
        them might take too long and we don't want to change products without
        the user knowing about it."""
        if 'create_variant' in vals:
            products = self._get_related_product_templates()
            if products:
                message = ', '.join(products.mapped('name'))
                raise UserError(_('You are trying to change the type of an attribute value still referenced on at least one product template: %s') % message)
        invalidate_cache = 'sequence' in vals and any(record.sequence != vals['sequence'] for record in self)
        res = super(ProductAttribute, self).write(vals)
        if invalidate_cache:
            # prefetched o2m have to be resequenced
            # (eg. product.template: attribute_line_ids)
            # DLE P81: `test_get_first_possible_combination`
            # `write` on `product.attribute.value` `sequence` field triggers and invalidate of the cache,
            # it appears the goal is to re-order the cached value for one2many field on `product.attribute.value`
            # Not sure if we change this specificaly in places calling `invalidate_cache()`
            # or if we do it generically in invalidate_cache. For the given test `test_get_first_possible_combination`,
            # there is several places where `invalidate_cache` is called manually.
            self.flush()
            self.invalidate_cache()
        return res

    def _get_related_product_templates(self):
        return self.env['product.template'].with_context(active_test=False).search([
            ('attribute_line_ids.attribute_id', 'in', self.ids),
        ])


class ProductAttributeValue(models.Model):
    _name = "product.attribute.value"
    # if you change this _order, keep it in sync with the method
    # `_sort_key_variant` in `product.template'
    _order = 'attribute_id, sequence, id'
    _description = 'Attribute Value'

    name = fields.Char(string='Value', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', help="Determine the display order", index=True)
    attribute_id = fields.Many2one('product.attribute', string='Attribute', ondelete='cascade', required=True, index=True)

    _sql_constraints = [
        ('value_company_uniq', 'unique (name, attribute_id)', 'This attribute value already exists !')
    ]

    def name_get(self):
        """Override because in general the name of the value is confusing if it
        is displayed without the name of the corresponding attribute.
        Eg. on product list & kanban views, on BOM form view

        However during variant set up (on the product template form) the name of
        the attribute is already on each line so there is no need to repeat it
        on every value.
        """
        if not self._context.get('show_attribute', True):
            return super(ProductAttributeValue, self).name_get()
        return [(value.id, "%s: %s" % (value.attribute_id.name, value.name)) for value in self]

    def _variant_name(self, variable_attributes):
        return ", ".join([v.name for v in self if v.attribute_id in variable_attributes])

    def write(self, values):
        invalidate_cache = 'sequence' in values and any(record.sequence != values['sequence'] for record in self)
        res = super(ProductAttributeValue, self).write(values)
        if invalidate_cache:
            # prefetched o2m have to be resequenced
            # (eg. product.template.attribute.line: value_ids)
            self.flush()
            self.invalidate_cache()
        return res

    def unlink(self):
        linked_products = self._get_related_product_templates()
        if linked_products:
            raise UserError(_('The operation cannot be completed:\nYou are trying to delete an attribute value with a reference on a product variant.'))
        return super(ProductAttributeValue, self).unlink()

    def _without_no_variant_attributes(self):
        return self.filtered(lambda pav: pav.attribute_id.create_variant != 'no_variant')

    def _get_related_product_templates(self):
        return self.env['product.template'].with_context(active_test=False).search([
            ('attribute_line_ids.value_ids', 'in', self.ids),
        ])


class ProductTemplateAttributeLine(models.Model):
    """Attributes available on product.template with their selected values in a m2m.
    Used as a configuration model to generate the appropriate product.template.attribute.value"""

    _name = "product.template.attribute.line"
    _rec_name = 'attribute_id'
    _description = 'Product Template Attribute Line'
    _order = 'attribute_id, id'

    product_tmpl_id = fields.Many2one('product.template', string='Product Template', ondelete='cascade', required=True, index=True)
    attribute_id = fields.Many2one('product.attribute', string='Attribute', ondelete='restrict', required=True, index=True)
    value_ids = fields.Many2many('product.attribute.value', string='Attribute Values')
    product_template_value_ids = fields.Many2many(
        'product.template.attribute.value',
        string='Product Attribute Values',
        compute="_set_product_template_value_ids",
        store=False)

    @api.constrains('value_ids', 'attribute_id')
    def _check_valid_attribute(self):
        if any(not line.value_ids or line.value_ids > line.attribute_id.value_ids for line in self):
            raise ValidationError(_('You cannot use this attribute with the following value.'))
        return True

    @api.model_create_multi
    def create(self, values):
        res = super(ProductTemplateAttributeLine, self).create(values)
        res._update_product_template_attribute_values()
        return res

    def write(self, values):
        res = super(ProductTemplateAttributeLine, self).write(values)
        self._update_product_template_attribute_values()
        return res

    @api.depends('value_ids')
    def _set_product_template_value_ids(self):
        for product_template_attribute_line in self:
            product_template_attribute_line.product_template_value_ids = self.env['product.template.attribute.value'].search([
                ('product_tmpl_id', 'in', product_template_attribute_line.product_tmpl_id.ids),
                ('product_attribute_value_id', 'in', product_template_attribute_line.value_ids.ids)]
            )

    def unlink(self):
        for product_template_attribute_line in self:
            self.env['product.template.attribute.value'].search([
                ('product_tmpl_id', 'in', product_template_attribute_line.product_tmpl_id.ids),
                ('product_attribute_value_id.attribute_id', 'in', product_template_attribute_line.value_ids.mapped('attribute_id').ids)]).unlink()

        return super(ProductTemplateAttributeLine, self).unlink()

    def _update_product_template_attribute_values(self):
        """
        Create or unlink product.template.attribute.value based on the attribute lines.
        If the product.attribute.value is removed, remove the corresponding product.template.attribute.value
        If no product.template.attribute.value exists for the newly added product.attribute.value, create it.
        """
        for attribute_line in self:
            # All existing product.template.attribute.value for this template
            product_template_attribute_values_to_remove = self.env['product.template.attribute.value'].search([
                ('product_tmpl_id', '=', attribute_line.product_tmpl_id.id),
                ('product_attribute_value_id.attribute_id', 'in', attribute_line.value_ids.mapped('attribute_id').ids)])
            # All existing product.attribute.value shared by all products
            # eg (Yellow, Red, Blue, Small, Large)
            existing_product_attribute_values = product_template_attribute_values_to_remove.mapped('product_attribute_value_id')

            # Loop on product.attribute.values for the line (eg: Yellow, Red, Blue)
            for product_attribute_value in attribute_line.value_ids:
                if product_attribute_value in existing_product_attribute_values:
                    # property is already existing: don't touch, remove it from list to avoid unlinking it
                    product_template_attribute_values_to_remove = product_template_attribute_values_to_remove.filtered(
                        lambda value: product_attribute_value not in value.mapped('product_attribute_value_id')
                    )
                else:
                    # property does not exist: create it
                    self.env['product.template.attribute.value'].create({
                        'product_attribute_value_id': product_attribute_value.id,
                        'product_tmpl_id': attribute_line.product_tmpl_id.id})

            # at this point, existing properties can be removed to reflect the modifications on value_ids
            if product_template_attribute_values_to_remove:
                product_template_attribute_values_to_remove.unlink()

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            args = args or []
            domain = ['|', ('attribute_id', operator, name), ('value_ids', operator, name)]
            attribute_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
            return self.browse(attribute_ids).name_get()
        return super(ProductTemplateAttributeLine, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    def _without_no_variant_attributes(self):
        return self.filtered(lambda ptal: ptal.attribute_id.create_variant != 'no_variant')


class ProductTemplateAttributeValue(models.Model):
    """Materialized relationship between attribute values
    and product template generated by the product.template.attribute.line"""

    _name = "product.template.attribute.value"
    _order = 'product_attribute_value_id, id'
    _description = 'Product Attribute Value'

    name = fields.Char('Value', related="product_attribute_value_id.name")
    product_attribute_value_id = fields.Many2one(
        'product.attribute.value', string='Attribute Value',
        required=True, ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template',
        required=True, ondelete='cascade', index=True)
    attribute_id = fields.Many2one(
        'product.attribute', string='Attribute',
        related="product_attribute_value_id.attribute_id")
    sequence = fields.Integer('Sequence', related="product_attribute_value_id.sequence")
    price_extra = fields.Float(
        string='Attribute Price Extra',
        default=0.0,
        digits='Product Price',
        help="""Price Extra: Extra price for the variant with
        this attribute value on sale price. eg. 200 price extra, 1000 + 200 = 1200.""")
    exclude_for = fields.One2many(
        'product.template.attribute.exclusion',
        'product_template_attribute_value_id',
        string="Exclude for",
        relation="product_template_attribute_exclusion",
        help="""Make this attribute value not compatible with
        other values of the product or some attribute values of optional and accessory products.""")

    def name_get(self):
        """Override because in general the name of the value is confusing if it
        is displayed without the name of the corresponding attribute.
        Eg. on exclusion rules form
        """
        return [(value.id, "%s: %s" % (value.attribute_id.name, value.name)) for value in self]

    def _without_no_variant_attributes(self):
        return self.filtered(lambda ptav: ptav.attribute_id.create_variant != 'no_variant')


class ProductTemplateAttributeExclusion(models.Model):
    _name = "product.template.attribute.exclusion"
    _description = 'Product Template Attribute Exclusion'

    product_template_attribute_value_id = fields.Many2one(
        'product.template.attribute.value', string="Attribute Value", ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template', ondelete='cascade', required=True, index=True)
    value_ids = fields.Many2many(
        'product.template.attribute.value', relation="product_attr_exclusion_value_ids_rel",
        string='Attribute Values', domain="[('product_tmpl_id', '=', product_tmpl_id)]")
