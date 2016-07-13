# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import time

import openerp
from openerp import api, tools, SUPERUSER_ID
from openerp.osv import osv, fields, expression
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import psycopg2

import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_round, float_compare
from openerp.exceptions import UserError
from openerp.exceptions import except_orm


class product_attribute(osv.osv):
    _name = "product.attribute"
    _description = "Product Attribute"
    _order = 'sequence, name'
    _columns = {
        'name': fields.char('Name', translate=True, required=True),
        'value_ids': fields.one2many('product.attribute.value', 'attribute_id', 'Values', copy=True),
        'sequence': fields.integer('Sequence', help="Determine the display order"),
        'attribute_line_ids': fields.one2many('product.attribute.line', 'attribute_id', 'Lines'),
    }

class product_attribute_value(osv.osv):
    _name = "product.attribute.value"
    _order = 'sequence'
    def _get_price_extra(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, 0)
        if not context.get('active_id'):
            return result

        for obj in self.browse(cr, uid, ids, context=context):
            for price_id in obj.price_ids:
                if price_id.product_tmpl_id.id == context.get('active_id'):
                    result[obj.id] = price_id.price_extra
                    break
        return result

    def _set_price_extra(self, cr, uid, id, name, value, args, context=None):
        if context is None:
            context = {}
        if 'active_id' not in context:
            return None
        p_obj = self.pool['product.attribute.price']
        p_ids = p_obj.search(cr, uid, [('value_id', '=', id), ('product_tmpl_id', '=', context['active_id'])], context=context)
        if p_ids:
            p_obj.write(cr, uid, p_ids, {'price_extra': value}, context=context)
        else:
            p_obj.create(cr, uid, {
                    'product_tmpl_id': context['active_id'],
                    'value_id': id,
                    'price_extra': value,
                }, context=context)

    def name_get(self, cr, uid, ids, context=None):
        if context and not context.get('show_attribute', True):
            return super(product_attribute_value, self).name_get(cr, uid, ids, context=context)
        res = []
        for value in self.browse(cr, uid, ids, context=context):
            res.append([value.id, "%s: %s" % (value.attribute_id.name, value.name)])
        return res

    _columns = {
        'sequence': fields.integer('Sequence', help="Determine the display order"),
        'name': fields.char('Value', translate=True, required=True),
        'attribute_id': fields.many2one('product.attribute', 'Attribute', required=True, ondelete='cascade'),
        'product_ids': fields.many2many('product.product', id1='att_id', id2='prod_id', string='Variants', readonly=True),
        'price_extra': fields.function(_get_price_extra, type='float', string='Attribute Price Extra',
            fnct_inv=_set_price_extra,
            digits_compute=dp.get_precision('Product Price'),
            help="Price Extra: Extra price for the variant with this attribute value on sale price. eg. 200 price extra, 1000 + 200 = 1200."),
        'price_ids': fields.one2many('product.attribute.price', 'value_id', string='Attribute Prices', readonly=True),
    }
    _sql_constraints = [
        ('value_company_uniq', 'unique (name,attribute_id)', 'This attribute value already exists !')
    ]
    _defaults = {
        'price_extra': 0.0,
    }
    def unlink(self, cr, uid, ids, context=None):
        ctx = dict(context or {}, active_test=False)
        product_ids = self.pool['product.product'].search(cr, uid, [('attribute_value_ids', 'in', ids)], context=ctx)
        if product_ids:
            raise UserError(_('The operation cannot be completed:\nYou are trying to delete an attribute value with a reference on a product variant.'))
        return super(product_attribute_value, self).unlink(cr, uid, ids, context=context)

class product_attribute_price(osv.osv):
    _name = "product.attribute.price"
    _columns = {
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', required=True, ondelete='cascade'),
        'value_id': fields.many2one('product.attribute.value', 'Product Attribute Value', required=True, ondelete='cascade'),
        'price_extra': fields.float('Price Extra', digits_compute=dp.get_precision('Product Price')),
    }

class product_attribute_line(osv.osv):
    _name = "product.attribute.line"
    _rec_name = 'attribute_id'
    _columns = {
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', required=True, ondelete='cascade'),
        'attribute_id': fields.many2one('product.attribute', 'Attribute', required=True, ondelete='restrict'),
        'value_ids': fields.many2many('product.attribute.value', id1='line_id', id2='val_id', string='Attribute Values'),
    }

    def _check_valid_attribute(self, cr, uid, ids, context=None):
        for obj_pal in self.browse(cr, uid, ids, context=context):
            if not (obj_pal.value_ids <= obj_pal.attribute_id.value_ids):
                return False
        return True

    _constraints = [
        (_check_valid_attribute, 'Error ! You cannot use this attribute with the following value.', ['attribute_id'])
    ]

    def name_search(self, cr, uid, name='', args=None, operator='ilike', context=None, limit=100):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            new_args = ['|', ('attribute_id', operator, name), ('value_ids', operator, name)]
        else:
            new_args = args
        return super(product_attribute_line, self).name_search(
            cr, uid, name=name,
            args=new_args,
            operator=operator, context=context, limit=limit)
