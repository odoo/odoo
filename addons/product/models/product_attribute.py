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
        ('always', 'Instantly'),
        ('dynamic', 'Dynamically'),
        ('no_variant', 'Never')],
        default='always',
        string="Variants Creation Mode",
        help="""- Instantly: All possible variants are created as soon as the attribute and its values are added to a product.
        - Dynamically: Each variant is created only when its corresponding attributes and values are added to a sales order.
        - Never: Variants are never created for the attribute.
        Note: the variants creation mode cannot be changed once the attribute is used on at least one product.""",
        required=True)
    is_used_on_products = fields.Boolean('Used on Products', compute='_compute_is_used_on_products')
    product_tmpl_ids = fields.Many2many('product.template', string="Related Products", compute='_compute_products', store=True)

    @api.depends('product_tmpl_ids')
    def _compute_is_used_on_products(self):
        for pa in self:
            pa.is_used_on_products = bool(pa.product_tmpl_ids)

    @api.depends('attribute_line_ids.product_tmpl_id')
    def _compute_products(self):
        for pa in self:
            pa.product_tmpl_ids = pa.attribute_line_ids.product_tmpl_id

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
            for pa in self:
                if vals['create_variant'] != pa.create_variant and pa.is_used_on_products:
                    raise UserError(
                        _("You cannot change the Variants Creation Mode of the attribute <strong>%s</strong> because it is used on the following products:\n%s") %
                        (pa.display_name, ", ".join(pa.product_tmpl_ids.mapped('display_name')))
                    )
        invalidate_cache = 'sequence' in vals and any(record.sequence != vals['sequence'] for record in self)
        res = super(ProductAttribute, self).write(vals)
        if invalidate_cache:
            # prefetched o2m have to be resequenced
            # (eg. product.template: attribute_line_ids)
            self.flush()
            self.invalidate_cache()
        return res

    def unlink(self):
        for pa in self:
            if pa.is_used_on_products:
                raise UserError(
                    _("You cannot delete the attribute <strong>%s</strong> because it is used on the following products:\n%s") %
                    (pa.display_name, ", ".join(pa.product_tmpl_ids.mapped('display_name')))
                )
        return super(ProductAttribute, self).unlink()


class ProductAttributeValue(models.Model):
    _name = "product.attribute.value"
    # if you change this _order, keep it in sync with the method
    # `_sort_key_variant` in `product.template'
    _order = 'attribute_id, sequence, id'
    _description = 'Attribute Value'

    name = fields.Char(string='Value', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', help="Determine the display order", index=True)
    attribute_id = fields.Many2one('product.attribute', string="Attribute", ondelete='cascade', required=True, index=True,
        help="The attribute cannot be changed once the value is used on at least one product.")

    pav_attribute_line_ids = fields.Many2many('product.template.attribute.line', string="Lines",
        relation='product_attribute_value_product_template_attribute_line_rel')
    is_used_on_products = fields.Boolean('Used on Products', compute='_compute_is_used_on_products')

    _sql_constraints = [
        ('value_company_uniq', 'unique (name, attribute_id)', "You cannot create two values with the same name for the same attribute.")
    ]

    @api.depends('pav_attribute_line_ids')
    def _compute_is_used_on_products(self):
        for pav in self:
            pav.is_used_on_products = bool(pav.pav_attribute_line_ids)

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
        if 'attribute_id' in values:
            for pav in self:
                if pav.attribute_id.id != values['attribute_id'] and pav.is_used_on_products:
                    raise UserError(
                        _("You cannot change the attribute of the value <strong>%s</strong> because it is used on the following products:%s") %
                        (pav.display_name, ", ".join(pav.pav_attribute_line_ids.product_tmpl_id.mapped('display_name')))
                    )

        invalidate_cache = 'sequence' in values and any(record.sequence != values['sequence'] for record in self)
        res = super(ProductAttributeValue, self).write(values)
        if invalidate_cache:
            # prefetched o2m have to be resequenced
            # (eg. product.template.attribute.line: value_ids)
            self.flush()
            self.invalidate_cache()
        return res

    def unlink(self):
        for pav in self:
            if pav.is_used_on_products:
                raise UserError(
                    _("You cannot delete the value <strong>%s</strong> because it is used on the following products:\n%s") %
                    (pav.display_name, ", ".join(pav.pav_attribute_line_ids.product_tmpl_id.mapped('display_name')))
                )
        return super(ProductAttributeValue, self).unlink()

    def _without_no_variant_attributes(self):
        return self.filtered(lambda pav: pav.attribute_id.create_variant != 'no_variant')


class ProductTemplateAttributeLine(models.Model):
    """Attributes available on product.template with their selected values in a m2m.
    Used as a configuration model to generate the appropriate product.template.attribute.value"""

    _name = "product.template.attribute.line"
    _rec_name = 'attribute_id'
    _description = 'Product Template Attribute Line'
    _order = 'attribute_id, id'

    product_tmpl_id = fields.Many2one('product.template', string="Product Template", ondelete='cascade', required=True, index=True)
    attribute_id = fields.Many2one('product.attribute', string="Attribute", ondelete='restrict', required=True, index=True)
    value_ids = fields.Many2many('product.attribute.value', string="Values", domain="[('attribute_id', '=', attribute_id)]",
        relation='product_attribute_value_product_template_attribute_line_rel')
    product_template_value_ids = fields.One2many('product.template.attribute.value', 'attribute_line_id', string="Product Attribute Values")

    @api.onchange('attribute_id')
    def _onchange_attribute_id(self):
        self.value_ids = self.value_ids.filtered(lambda pav: pav.attribute_id == self.attribute_id)

    @api.constrains('value_ids', 'attribute_id')
    def _check_valid_values(self):
        for ptal in self:
            if not ptal.value_ids:
                raise ValidationError(
                    _("The attribute <strong>%s</strong> must have at least one value for the product %s.") %
                    (ptal.attribute_id.display_name, ptal.product_tmpl_id.display_name)
                )
            for pav in ptal.value_ids:
                if pav.attribute_id != ptal.attribute_id:
                    raise ValidationError(
                        _("On the product %s you cannot associate the value <strong>%s</strong> with the attribute <strong>%s</strong> because they do not match.") %
                        (ptal.product_tmpl_id.display_name, pav.display_name, ptal.attribute_id.display_name)
                    )
        return True

    @api.model_create_multi
    def create(self, values):
        res = super(ProductTemplateAttributeLine, self).create(values)
        res._update_product_template_attribute_values()
        return res

    def write(self, values):
        if 'product_tmpl_id' in values:
            for ptal in self:
                if ptal.product_tmpl_id.id != values['product_tmpl_id']:
                    raise UserError(
                        _("You cannot move the attribute <strong>%s</strong> from the product %s to the product %s.") %
                        (ptal.attribute_id.display_name, ptal.product_tmpl_id.display_name, values['product_tmpl_id'])
                    )

        if 'attribute_id' in values:
            for ptal in self:
                if ptal.attribute_id.id != values['attribute_id']:
                    raise UserError(
                        _("On the product %s you cannot transform the attribute <strong>%s</strong> into the attribute %s.") %
                        (ptal.product_tmpl_id.display_name, ptal.attribute_id.display_name, values['attribute_id'])
                    )

        res = super(ProductTemplateAttributeLine, self).write(values)
        self._update_product_template_attribute_values()
        return res

    def _update_product_template_attribute_values(self):
        """Create or unlink `product.template.attribute.value` for each line in
        `self` based on `value_ids`.

        This is a trick for the form view and for performance in general,
        because we don't want to generate in advance all possible values for all
        templates, but only those that will be selected.
        """
        ptav_to_create = []
        ptav_to_unlink = self.env['product.template.attribute.value']

        for ptal in self:
            existing_pav = self.env['product.attribute.value']
            for ptav in ptal.product_template_value_ids:
                if ptav.product_attribute_value_id not in ptal.value_ids:
                    # remove values that existed but don't exist anymore
                    ptav_to_unlink += ptav
                else:
                    existing_pav += ptav.product_attribute_value_id

            for pav in (ptal.value_ids - existing_pav):
                # create values that didn't exist yet
                ptav_to_create.append({
                    'product_attribute_value_id': pav.id,
                    'attribute_line_id': ptal.id
                })

        # unlink and create in batch for performance
        ptav_to_unlink.unlink()
        self.env['product.template.attribute.value'].create(ptav_to_create)

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
    _description = "Product Template Attribute Value"
    _order = 'product_attribute_value_id, id'

    name = fields.Char('Value', related="product_attribute_value_id.name")

    # defining fields: the product template attribute line and the product attribute value
    product_attribute_value_id = fields.Many2one(
        'product.attribute.value', string='Attribute Value',
        required=True, ondelete='restrict', index=True)
    attribute_line_id = fields.Many2one('product.template.attribute.line', required=True, ondelete='cascade', index=True)

    # configuration fields: the price_extra and the exclusion rules
    price_extra = fields.Float(
        string="Value Price Extra",
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

    # related fields: product template and product attribute
    product_tmpl_id = fields.Many2one('product.template', string="Product Template", related='attribute_line_id.product_tmpl_id', store=True, index=True)
    attribute_id = fields.Many2one('product.attribute', string="Attribute", related='attribute_line_id.attribute_id', store=True, index=True)

    _sql_constraints = [
        ('attribute_value_unique', 'unique(attribute_line_id, product_attribute_value_id)', "Each value should be defined only once per attribute per product."),
    ]

    @api.constrains('attribute_line_id', 'product_attribute_value_id')
    def _check_valid_values(self):
        for ptav in self:
            if ptav.product_attribute_value_id not in ptav.attribute_line_id.value_ids:
                raise ValidationError(
                    _("The value <strong>%s</strong> is not defined for the attribute <strong>%s</strong> on the product %s.") %
                    (ptav.product_attribute_value_id.display_name, ptav.attribute_id.display_name, ptav.product_tmpl_id.display_name)
                )

    def write(self, values):
        pav_in_values = 'product_attribute_value_id' in values
        product_in_values = 'product_tmpl_id' in values
        if pav_in_values or product_in_values:
            for ptav in self:
                if pav_in_values and ptav.product_attribute_value_id.id != values['product_attribute_value_id']:
                    raise UserError(
                        _("You cannot change the value of the value <strong>%s</strong> set on product %s.") %
                        (ptav.display_name, ptav.product_tmpl_id.display_name)
                    )
                if product_in_values and ptav.product_tmpl_id.id != values['product_tmpl_id']:
                    raise UserError(
                        _("You cannot change the product of the value <strong>%s</strong> set on product %s.") %
                        (ptav.display_name, ptav.product_tmpl_id.display_name)
                    )

        return super(ProductTemplateAttributeValue, self).write(values)

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
