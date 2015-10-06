# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _

import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError


class ProductAttribute(models.Model):
    _name = "product.attribute"
    _description = "Product Attribute"
    _order = 'sequence,id'

    name = fields.Char(translate=True, required=True)
    value_ids = fields.One2many('product.attribute.value', 'attribute_id', string='Values', copy=True)
    sequence = fields.Integer(help="Determine the display order")
    attribute_line_ids = fields.One2many('product.attribute.line', 'attribute_id', string='Lines')


class ProductAttributeValue(models.Model):
    _name = "product.attribute.value"
    _order = 'sequence'

    sequence = fields.Integer(help="Determine the display order")
    name = fields.Char(string='Value', translate=True, required=True)
    attribute_id = fields.Many2one('product.attribute', string='Attribute', required=True, ondelete='cascade')
    product_ids = fields.Many2many('product.product', column1='att_id', column2='prod_id', string='Variants', readonly=True)
    price_extra = fields.Float(compute='_compute_price_extra', string='Attribute Price Extra', inverse='_inverse_price_extra',
        digits_compute=dp.get_precision('Product Price'), default=0.0,
        help="Price Extra: Extra price for the variant with this attribute value on sale price. eg. 200 price extra, 1000 + 200 = 1200.")
    price_ids = fields.One2many('product.attribute.price', 'value_id', string='Attribute Prices', readonly=True)

    _sql_constraints = [
        ('value_company_uniq', 'unique (name,attribute_id)', 'This attribute value already exists !')
    ]

    @api.multi
    def _compute_price_extra(self):
        if self._context.get('active_id'):
            for Pattr_price in self:
                for price_id in Pattr_price.price_ids:
                    if price_id.product_tmpl_id.id == self._context.get('active_id'):
                        Pattr_price.price_extra = price_id.price_extra

    def _inverse_price_extra(self):
        if self._context.get('active_id'):
            product_attr_price = self.env['product.attribute.price']
            product_attr_ids = product_attr_price.search([('value_id', '=', self.id), ('product_tmpl_id', '=', self._context['active_id'])])
            if product_attr_ids:
                product_attr_ids.write({'price_extra': self.price_extra})
            else:
                product_attr_price.create({
                        'product_tmpl_id': self._context['active_id'],
                        'value_id': self.id,
                        'price_extra': self.price_extra})

    @api.multi
    def name_get(self):
        if self._context and not self._context.get('show_attribute', True):
            return super(ProductAttributeValue, self).name_get()
        res = []
        for value in self:
            res.append([value.id, "%s: %s" % (value.attribute_id.name, value.name)])
        return res

    @api.multi
    def unlink(self):
        product_ids = self.env['product.product'].with_context(active_test=False).search([('attribute_value_ids', 'in', self.ids)])
        if product_ids:
            raise UserError(_('The operation cannot be completed:\nYou are trying to delete an attribute value with a reference on a product variant.'))
        return super(ProductAttributeValue, self).unlink()

class ProductAttributePrice(models.Model):
    _name = "product.attribute.price"

    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True, ondelete='cascade')
    value_id = fields.Many2one('product.attribute.value', string='Product Attribute Value', required=True, ondelete='cascade')
    price_extra = fields.Float(string='Price Extra', digits_compute=dp.get_precision('Product Price'))

class ProductAttributeLine(models.Model):
    _name = "product.attribute.line"
    _rec_name = 'attribute_id'

    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True, ondelete='cascade')
    attribute_id = fields.Many2one('product.attribute', string='Attribute', required=True, ondelete='restrict')
    value_ids = fields.Many2many('product.attribute.value', column1='line_id', column2='val_id', string='Attribute Values')

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
