# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError


class ProductAttribute(models.Model):
    _name = "product.attribute"
    _description = "Product Attribute"
    _order = 'sequence, name'

    name = fields.Char('Name', required=True, translate=True)
    value_ids = fields.One2many('product.attribute.value', 'attribute_id', 'Values', copy=True)
    sequence = fields.Integer('Sequence', help="Determine the display order")
    attribute_line_ids = fields.One2many('product.attribute.line', 'attribute_id', 'Lines')
    create_variant = fields.Boolean(default=True, help="Check this if you want to create multiple variants for this attribute.")


class ProductAttributevalue(models.Model):
    _name = "product.attribute.value"
    _order = 'sequence, attribute_id, id'

    name = fields.Char('Value', required=True, translate=True)
    sequence = fields.Integer('Sequence', help="Determine the display order")
    attribute_id = fields.Many2one('product.attribute', 'Attribute', ondelete='cascade', required=True)
    product_ids = fields.Many2many('product.product', string='Variants', readonly=True)
    price_extra = fields.Float(
        'Attribute Price Extra', compute='_compute_price_extra', inverse='_set_price_extra',
        default=0.0, digits=dp.get_precision('Product Price'),
        help="Price Extra: Extra price for the variant with this attribute value on sale price. eg. 200 price extra, 1000 + 200 = 1200.")
    price_ids = fields.One2many('product.attribute.price', 'value_id', 'Attribute Prices', readonly=True)

    _sql_constraints = [
        ('value_company_uniq', 'unique (name,attribute_id)', 'This attribute value already exists !')
    ]

    @api.one
    def _compute_price_extra(self):
        if self._context.get('active_id'):
            price = self.price_ids.filtered(lambda price: price.product_tmpl_id.id == self._context['active_id'])
            self.price_extra = price.price_extra
        else:
            self.price_extra = 0.0

    def _set_price_extra(self):
        if not self._context.get('active_id'):
            return

        AttributePrice = self.env['product.attribute.price']
        prices = AttributePrice.search([('value_id', 'in', self.ids), ('product_tmpl_id', '=', self._context['active_id'])])
        updated = prices.mapped('value_id')
        if prices:
            prices.write({'price_extra': self.price_extra})
        else:
            for value in self - updated:
                AttributePrice.create({
                    'product_tmpl_id': self._context['active_id'],
                    'value_id': value.id,
                    'price_extra': self.price_extra,
                })

    @api.multi
    def name_get(self):
        if not self._context.get('show_attribute', True):  # TDE FIXME: not used
            return super(ProductAttributevalue, self).name_get()
        return [(value.id, "%s: %s" % (value.attribute_id.name, value.name)) for value in self]

    @api.multi
    def unlink(self):
        linked_products = self.env['product.product'].with_context(active_test=False).search([('attribute_value_ids', 'in', self.ids)])
        if linked_products:
            raise UserError(_('The operation cannot be completed:\nYou are trying to delete an attribute value with a reference on a product variant.'))
        return super(ProductAttributevalue, self).unlink()

    @api.multi
    def _variant_name(self, variable_attributes):
        return ", ".join([v.name for v in self if v.attribute_id in variable_attributes])


class ProductAttributePrice(models.Model):
    _name = "product.attribute.price"

    product_tmpl_id = fields.Many2one('product.template', 'Product Template', ondelete='cascade', required=True)
    value_id = fields.Many2one('product.attribute.value', 'Product Attribute Value', ondelete='cascade', required=True)
    price_extra = fields.Float('Price Extra', digits=dp.get_precision('Product Price'))


class ProductAttributeLine(models.Model):
    _name = "product.attribute.line"
    _rec_name = 'attribute_id'

    product_tmpl_id = fields.Many2one('product.template', 'Product Template', ondelete='cascade', required=True)
    attribute_id = fields.Many2one('product.attribute', 'Attribute', ondelete='restrict', required=True)
    value_ids = fields.Many2many('product.attribute.value', string='Attribute Values')

    @api.constrains('value_ids', 'attribute_id')
    def _check_valid_attribute(self):
        if any(line.value_ids > line.attribute_id.value_ids for line in self):
            raise ValidationError(_('Error ! You cannot use this attribute with the following value.'))
        return True

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            new_args = ['|', ('attribute_id', operator, name), ('value_ids', operator, name)]
        else:
            new_args = args
        return super(ProductAttributeLine, self).name_search(name=name, args=new_args, operator=operator, limit=limit)
