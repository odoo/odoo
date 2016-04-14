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

#----------------------------------------------------------
# UOM
#----------------------------------------------------------

class product_uom_categ(osv.osv):
    _name = 'product.uom.categ'
    _description = 'Product uom categ'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
    }

class product_uom(osv.osv):
    _name = 'product.uom'
    _description = 'Product Unit of Measure'

    def _compute_factor_inv(self, factor):
        return factor and (1.0 / factor) or 0.0

    def _factor_inv(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for uom in self.browse(cursor, user, ids, context=context):
            res[uom.id] = self._compute_factor_inv(uom.factor)
        return res

    def _factor_inv_write(self, cursor, user, id, name, value, arg, context=None):
        return self.write(cursor, user, id, {'factor': self._compute_factor_inv(value)}, context=context)

    def name_create(self, cr, uid, name, context=None):
        """ The UoM category and factor are required, so we'll have to add temporary values
            for imported UoMs """
        if not context:
            context = {}
        uom_categ = self.pool.get('product.uom.categ')
        values = {self._rec_name: name, 'factor': 1}
        # look for the category based on the english name, i.e. no context on purpose!
        # TODO: should find a way to have it translated but not created until actually used
        if not context.get('default_category_id'):
            categ_misc = 'Unsorted/Imported Units'
            categ_id = uom_categ.search(cr, uid, [('name', '=', categ_misc)])
            if categ_id:
                values['category_id'] = categ_id[0]
            else:
                values['category_id'] = uom_categ.name_create(
                    cr, uid, categ_misc, context=context)[0]
        uom_id = self.create(cr, uid, values, context=context)
        return self.name_get(cr, uid, [uom_id], context=context)[0]

    def create(self, cr, uid, data, context=None):
        if 'factor_inv' in data:
            if data['factor_inv'] != 1:
                data['factor'] = self._compute_factor_inv(data['factor_inv'])
            del(data['factor_inv'])
        return super(product_uom, self).create(cr, uid, data, context)

    _order = "name"
    _columns = {
        'name': fields.char('Unit of Measure', required=True, translate=True),
        'category_id': fields.many2one('product.uom.categ', 'Unit of Measure Category', required=True, ondelete='cascade',
            help="Conversion between Units of Measure can only occur if they belong to the same category. The conversion will be made based on the ratios."),
        'factor': fields.float('Ratio', required=True, digits=0, # force NUMERIC with unlimited precision
            help='How much bigger or smaller this unit is compared to the reference Unit of Measure for this category:\n'\
                    '1 * (reference unit) = ratio * (this unit)'),
        'factor_inv': fields.function(_factor_inv, digits=0, # force NUMERIC with unlimited precision
            fnct_inv=_factor_inv_write,
            string='Bigger Ratio',
            help='How many times this Unit of Measure is bigger than the reference Unit of Measure in this category:\n'\
                    '1 * (this unit) = ratio * (reference unit)', required=True),
        'rounding': fields.float('Rounding Precision', digits=0, required=True,
            help="The computed quantity will be a multiple of this value. "\
                 "Use 1.0 for a Unit of Measure that cannot be further split, such as a piece."),
        'active': fields.boolean('Active', help="By unchecking the active field you can disable a unit of measure without deleting it."),
        'uom_type': fields.selection([('bigger','Bigger than the reference Unit of Measure'),
                                      ('reference','Reference Unit of Measure for this category'),
                                      ('smaller','Smaller than the reference Unit of Measure')],'Type', required=1),
    }

    _defaults = {
        'active': 1,
        'rounding': 0.01,
        'factor': 1,
        'uom_type': 'reference',
        'factor': 1.0,
    }

    _sql_constraints = [
        ('factor_gt_zero', 'CHECK (factor!=0)', 'The conversion ratio for a unit of measure cannot be 0!')
    ]

    def _compute_qty(self, cr, uid, from_uom_id, qty, to_uom_id=False, round=True, rounding_method='UP'):
        if not from_uom_id or not qty or not to_uom_id:
            return qty
        uoms = self.browse(cr, uid, [from_uom_id, to_uom_id])
        if uoms[0].id == from_uom_id:
            from_unit, to_unit = uoms[0], uoms[-1]
        else:
            from_unit, to_unit = uoms[-1], uoms[0]
        return self._compute_qty_obj(cr, uid, from_unit, qty, to_unit, round=round, rounding_method=rounding_method)

    def _compute_qty_obj(self, cr, uid, from_unit, qty, to_unit, round=True, rounding_method='UP', context=None):
        if context is None:
            context = {}
        if from_unit.category_id.id != to_unit.category_id.id:
            if context.get('raise-exception', True):
                raise UserError(_('Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!.') % (from_unit.name,to_unit.name))
            else:
                return qty
        amount = qty/from_unit.factor
        if to_unit:
            amount = amount * to_unit.factor
            if round:
                amount = float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)
        return amount

    def _compute_price(self, cr, uid, from_uom_id, price, to_uom_id=False):
        if (not from_uom_id or not price or not to_uom_id
                or (to_uom_id == from_uom_id)):
            return price
        from_unit, to_unit = self.browse(cr, uid, [from_uom_id, to_uom_id])
        if from_unit.category_id.id != to_unit.category_id.id:
            return price
        amount = price * from_unit.factor
        if to_uom_id:
            amount = amount / to_unit.factor
        return amount

    def onchange_type(self, cursor, user, ids, value):
        if value == 'reference':
            return {'value': {'factor': 1, 'factor_inv': 1}}
        return {}

#----------------------------------------------------------
# Categories
#----------------------------------------------------------
class product_category(osv.osv):

    @api.multi
    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.parent_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.parent_id
            return res

        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        if name:
            # Be sure name_search is symetric to name_get
            categories = name.split(' / ')
            parents = list(categories)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(cr, uid, ' / '.join(parents), args=args, operator='ilike', context=context, limit=limit)
                category_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    category_ids = self.search(cr, uid, [('id', 'not in', category_ids)])
                    domain = expression.OR([[('parent_id', 'in', category_ids)], domain])
                else:
                    domain = expression.AND([[('parent_id', 'in', category_ids)], domain])
                for i in range(1, len(categories)):
                    domain = [[('name', operator, ' / '.join(categories[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            ids = self.search(cr, uid, expression.AND([domain, args]), limit=limit, context=context)
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _name = "product.category"
    _description = "Product Category"
    _columns = {
        'name': fields.char('Name', required=True, translate=True, select=True),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Name'),
        'parent_id': fields.many2one('product.category','Parent Category', select=True, ondelete='cascade'),
        'child_id': fields.one2many('product.category', 'parent_id', string='Child Categories'),
        'sequence': fields.integer('Sequence', select=True, help="Gives the sequence order when displaying a list of product categories."),
        'type': fields.selection([('view','View'), ('normal','Normal')], 'Category Type', help="A category of the view type is a virtual category that can be used as the parent of another category to create a hierarchical structure."),
        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),
    }


    _defaults = {
        'type' : 'normal',
    }

    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = 'parent_left'

    _constraints = [
        (osv.osv._check_recursion, 'Error ! You cannot create recursive categories.', ['parent_id'])
    ]


class produce_price_history(osv.osv):
    """
    Keep track of the ``product.template`` standard prices as they are changed.
    """

    _name = 'product.price.history'
    _rec_name = 'datetime'
    _order = 'datetime desc'

    _columns = {
        'company_id': fields.many2one('res.company', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True, ondelete='cascade'),
        'datetime': fields.datetime('Date'),
        'cost': fields.float('Cost'),
    }

    def _get_default_company(self, cr, uid, context=None):
        if 'force_company' in context:
            return context['force_company']
        else:
            company = self.pool['res.users'].browse(cr, uid, uid,
                context=context).company_id
            return company.id if company else False

    _defaults = {
        'datetime': fields.datetime.now,
        'company_id': _get_default_company,
    }


#----------------------------------------------------------
# Product Attributes
#----------------------------------------------------------
class product_attribute(osv.osv):
    _name = "product.attribute"
    _description = "Product Attribute"
    _order = 'sequence,id'
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


#----------------------------------------------------------
# Products
#----------------------------------------------------------
class product_template(osv.osv):
    _name = "product.template"
    _inherit = ['mail.thread']
    _description = "Product Template"
    _order = "name"

    def _is_product_variant(self, cr, uid, ids, name, arg, context=None):
        return self._is_product_variant_impl(cr, uid, ids, name, arg, context=context)

    def _is_product_variant_impl(self, cr, uid, ids, name, arg, context=None):
        return dict.fromkeys(ids, False)

    def _product_template_price(self, cr, uid, ids, name, arg, context=None):
        plobj = self.pool.get('product.pricelist')
        res = {}
        quantity = context.get('quantity') or 1.0
        pricelist = context.get('pricelist', False)
        partner = context.get('partner', False)
        if pricelist:
            # Support context pricelists specified as display_name or ID for compatibility
            if isinstance(pricelist, basestring):
                pricelist_ids = plobj.name_search(
                    cr, uid, pricelist, operator='=', context=context, limit=1)
                pricelist = pricelist_ids[0][0] if pricelist_ids else pricelist

            if isinstance(pricelist, (int, long)):
                products = self.browse(cr, uid, ids, context=context)
                qtys = map(lambda x: (x, quantity, partner), products)
                pl = plobj.browse(cr, uid, pricelist, context=context)
                price = plobj._price_get_multi(cr, uid, pl, qtys, context=context)
                for id in ids:
                    res[id] = price.get(id, 0.0)
        for id in ids:
            res.setdefault(id, 0.0)
        return res

    def _set_product_template_price(self, cr, uid, id, name, value, args, context=None):
        product_uom_obj = self.pool.get('product.uom')

        product = self.browse(cr, uid, id, context=context)
        if 'uom' in context:
            uom = product.uom_id
            value = product_uom_obj._compute_price(cr, uid,
                    context['uom'], value, uom.id)

        return product.write({'list_price': value})

    def _product_currency(self, cr, uid, ids, name, arg, context=None):
        uid = SUPERUSER_ID
        try:
            main_company = self.pool['ir.model.data'].get_object(cr, uid, 'base', 'main_company')
        except ValueError:
            company_ids = self.pool['res.company'].search(cr, uid, [], limit=1, order="id", context=context)
            main_company = self.pool['res.company'].browse(cr, uid, company_ids[0], context=context)
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = product.company_id.currency_id.id or main_company.currency_id.id
        return res

    def _get_product_variant_count(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = len(product.product_variant_ids)
        return res

    def _compute_product_template_field(self, cr, uid, ids, names, arg, context=None):
        ''' Compute the field from the product_variant if there is only one variant, otherwise returns 0.0 '''
        if isinstance(names, basestring):
            names = [names]
        res = {id: {} for id in ids}
        templates = self.browse(cr, uid, ids, context=context)
        unique_templates = [template.id for template in templates if template.product_variant_count == 1]
        for template in templates:
            for name in names:
                res[template.id][name] = getattr(template.product_variant_ids[0], name) if template.id in unique_templates else 0.0
        return res

    def _set_product_template_field(self, cr, uid, product_tmpl_id, name, value, args, context=None):
        ''' Set the standard price modification on the variant if there is only one variant '''
        template = self.pool['product.template'].browse(cr, uid, product_tmpl_id, context=context)
        if template.product_variant_count == 1:
            variant = self.pool['product.product'].browse(cr, uid, template.product_variant_ids.id, context=context)
            return variant.write({name: value})
        return {}

    def _search_by_standard_price(self, cr, uid, obj, name, domain, context=None):
        r = self.pool['product.product'].search_read(cr, uid, domain, ['product_tmpl_id'],
                                                     limit=None, context=context)
        return [('id', 'in', [x['product_tmpl_id'][0] for x in r])]

    def _get_template_id_from_product(self, cr, uid, ids, context=None):
        r = self.pool['product.product'].read(cr, uid, ids, ['product_tmpl_id'], context=context)
        return [x['product_tmpl_id'][0] for x in r]

    def _get_product_template_type(self, cr, uid, context=None):
        return [('consu', _('Consumable')), ('service', _('Service'))]
    _get_product_template_type_wrapper = lambda self, *args, **kwargs: self._get_product_template_type(*args, **kwargs)

    _columns = {
        'name': fields.char('Name', required=True, translate=True, select=True),
        'sequence': fields.integer('Sequence', help='Gives the sequence order when displaying a product list'),
        'product_manager': fields.many2one('res.users','Product Manager'),
        'description': fields.text('Description',translate=True,
            help="A precise description of the Product, used only for internal information purposes."),
        'description_purchase': fields.text('Purchase Description',translate=True,
            help="A description of the Product that you want to communicate to your vendors. "
                 "This description will be copied to every Purchase Order, Receipt and Vendor Bill/Refund."),
        'description_sale': fields.text('Sale Description',translate=True,
            help="A description of the Product that you want to communicate to your customers. "
                 "This description will be copied to every Sale Order, Delivery Order and Customer Invoice/Refund"),
        'type': fields.selection(_get_product_template_type_wrapper, 'Product Type', required=True,
            help="A consumable is a product for which you don't manage stock, a service is a non-material product provided by a company or an individual."),
        'rental': fields.boolean('Can be Rent'),
        'categ_id': fields.many2one('product.category','Internal Category', required=True, change_default=True, domain="[('type','=','normal')]" ,help="Select category for the current product"),
        'price': fields.function(_product_template_price, fnct_inv=_set_product_template_price, type='float', string='Price', digits_compute=dp.get_precision('Product Price')),
        'currency_id': fields.function(_product_currency, type='many2one', relation='res.currency', string='Currency'),
        'list_price': fields.float('Sale Price', digits_compute=dp.get_precision('Product Price'), help="Base price to compute the customer price. Sometimes called the catalog price."),
        'lst_price' : fields.related('list_price', type="float", string='Public Price', digits_compute=dp.get_precision('Product Price')),
        'standard_price': fields.function(_compute_product_template_field, fnct_inv=_set_product_template_field, fnct_search=_search_by_standard_price, multi='_compute_product_template_field', type='float', string='Cost', digits_compute=dp.get_precision('Product Price'),
                                          help="Cost of the product, in the default unit of measure of the product.", groups="base.group_user"),
        'volume': fields.function(_compute_product_template_field, fnct_inv=_set_product_template_field, multi='_compute_product_template_field', type='float', string='Volume', help="The volume in m3.", store={
            _name: (lambda s,c,u,i,t: i, ['product_variant_ids'], 10),
            'product.product': (_get_template_id_from_product, ['product_tmpl_id', 'volume'], 10),
        }),
        'weight': fields.function(_compute_product_template_field, fnct_inv=_set_product_template_field, multi='_compute_product_template_field', type='float', string='Gross Weight', digits_compute=dp.get_precision('Stock Weight'), help="The weight of the contents in Kg, not including any packaging, etc.", store={
            _name: (lambda s,c,u,i,t: i, ['product_variant_ids'], 10),
            'product.product': (_get_template_id_from_product, ['product_tmpl_id', 'weight'], 10),
        }),
        'warranty': fields.float('Warranty'),
        'sale_ok': fields.boolean('Can be Sold', help="Specify if the product can be selected in a sales order line."),
        'pricelist_id': fields.dummy(string='Pricelist', relation='product.pricelist', type='many2one'),
        'state': fields.selection([('draft', 'In Development'),
            ('sellable','Normal'),
            ('end','End of Lifecycle'),
            ('obsolete','Obsolete')], 'Status'),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True, help="Default Unit of Measure used for all stock operation."),
        'uom_po_id': fields.many2one('product.uom', 'Purchase Unit of Measure', required=True, help="Default Unit of Measure used for purchase orders. It must be in the same category than the default unit of measure."),
        'company_id': fields.many2one('res.company', 'Company', select=1),
        'packaging_ids': fields.one2many(
            'product.packaging', 'product_tmpl_id', 'Logistical Units',
            help="Gives the different ways to package the same product. This has no impact on "
                 "the picking order and is mainly used if you use the EDI module."),
        'seller_ids': fields.one2many('product.supplierinfo', 'product_tmpl_id', 'Vendor'),

        'active': fields.boolean('Active', help="If unchecked, it will allow you to hide the product without removing it."),
        'color': fields.integer('Color Index'),
        'is_product_variant': fields.function(_is_product_variant, type='boolean', string='Is a product variant'),

        'attribute_line_ids': fields.one2many('product.attribute.line', 'product_tmpl_id', 'Product Attributes'),
        'product_variant_ids': fields.one2many('product.product', 'product_tmpl_id', 'Products', required=True),
        'product_variant_count': fields.function(_get_product_variant_count, type='integer', string='# of Product Variants'),

        # related to display product product information if is_product_variant
        'barcode': fields.related('product_variant_ids', 'barcode', type='char', string='Barcode', oldname='ean13'),
        'default_code': fields.related('product_variant_ids', 'default_code', type='char', string='Internal Reference'),
        'item_ids': fields.one2many('product.pricelist.item', 'product_tmpl_id', 'Pricelist Items'),
    }

    # image: all image fields are base64 encoded and PIL-supported
    image = openerp.fields.Binary("Image", attachment=True,
        help="This field holds the image used as image for the product, limited to 1024x1024px.")
    image_medium = openerp.fields.Binary("Medium-sized image", attachment=True,
        help="Medium-sized image of the product. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved, "\
             "only when the image exceeds one of those sizes. Use this field in form views or some kanban views.")
    image_small = openerp.fields.Binary("Small-sized image", attachment=True,
        help="Small-sized image of the product. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

    def _price_get(self, cr, uid, products, ptype='list_price', context=None):
        if context is None:
            context = {}

        res = {}
        product_uom_obj = self.pool.get('product.uom')
        for product in products:
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            if ptype != 'standard_price':
                res[product.id] = product[ptype] or 0.0
            else:
                company_id = context.get('force_company') or product.env.user.company_id.id
                product = product.with_context(force_company=company_id)
                res[product.id] = res[product.id] = product.sudo()[ptype]
            if ptype == 'list_price':
                res[product.id] += product._name == "product.product" and product.price_extra or 0.0
            if 'uom' in context:
                uom = product.uom_id
                res[product.id] = product_uom_obj._compute_price(cr, uid,
                        uom.id, res[product.id], context['uom'])
            # Convert from current user company currency to asked one
            if 'currency_id' in context:
                # Take current user company currency.
                # This is right cause a field cannot be in more than one currency
                res[product.id] = self.pool.get('res.currency').compute(cr, uid, product.currency_id.id,
                    context['currency_id'], res[product.id], context=context)
        return res

    def _get_uom_id(self, cr, uid, *args):
        return self.pool["product.uom"].search(cr, uid, [], limit=1, order='id')[0]

    def _default_category(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'categ_id' in context and context['categ_id']:
            return context['categ_id']
        md = self.pool.get('ir.model.data')
        res = False
        try:
            res = md.get_object_reference(cr, uid, 'product', 'product_category_all')[1]
        except ValueError:
            res = False
        return res

    def onchange_type(self, cr, uid, ids, type, context=None):
        return {'value': {}}

    def onchange_uom(self, cursor, user, ids, uom_id, uom_po_id):
        if uom_id:
            return {'value': {'uom_po_id': uom_id}}
        return {}

    def create_variant_ids(self, cr, uid, ids, context=None):
        product_obj = self.pool.get("product.product")
        ctx = context and context.copy() or {}
        if ctx.get("create_product_variant"):
            return None

        ctx.update(active_test=False, create_product_variant=True)

        tmpl_ids = self.browse(cr, uid, ids, context=ctx)
        for tmpl_id in tmpl_ids:

            # list of values combination
            variant_alone = []
            all_variants = [[]]
            for variant_id in tmpl_id.attribute_line_ids:
                if len(variant_id.value_ids) == 1:
                    variant_alone.append(variant_id.value_ids[0])
                temp_variants = []
                for variant in all_variants:
                    for value_id in variant_id.value_ids:
                        temp_variants.append(sorted(variant + [int(value_id)]))
                if temp_variants:
                    all_variants = temp_variants

            # adding an attribute with only one value should not recreate product
            # write this attribute on every product to make sure we don't lose them
            for variant_id in variant_alone:
                product_ids = []
                for product_id in tmpl_id.product_variant_ids:
                    if not variant_id.attribute_id <= product_id.mapped('attribute_value_ids').mapped('attribute_id'):
                        product_ids.append(product_id.id)
                product_obj.write(cr, uid, product_ids, {'attribute_value_ids': [(4, variant_id.id)]}, context=ctx)

            # check product
            variant_ids_to_active = []
            variants_active_ids = []
            variants_inactive = []
            for product_id in tmpl_id.product_variant_ids:
                variants = sorted(map(int,product_id.attribute_value_ids))
                if variants in all_variants:
                    variants_active_ids.append(product_id.id)
                    all_variants.pop(all_variants.index(variants))
                    if not product_id.active:
                        variant_ids_to_active.append(product_id.id)
                else:
                    variants_inactive.append(product_id)
            if variant_ids_to_active:
                product_obj.write(cr, uid, variant_ids_to_active, {'active': True}, context=ctx)

            # create new product
            for variant_ids in all_variants:
                values = {
                    'product_tmpl_id': tmpl_id.id,
                    'attribute_value_ids': [(6, 0, variant_ids)]
                }
                id = product_obj.create(cr, uid, values, context=ctx)
                variants_active_ids.append(id)

            # unlink or inactive product
            for variant_id in map(int,variants_inactive):
                try:
                    with cr.savepoint(), tools.mute_logger('openerp.sql_db'):
                        product_obj.unlink(cr, uid, [variant_id], context=ctx)
                #We catch all kind of exception to be sure that the operation doesn't fail.
                except (psycopg2.Error, except_orm):
                    product_obj.write(cr, uid, [variant_id], {'active': False}, context=ctx)
                    pass
        return True

    def create(self, cr, uid, vals, context=None):
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        tools.image_resize_images(vals)
        product_template_id = super(product_template, self).create(cr, uid, vals, context=context)
        if not context or "create_product_product" not in context:
            self.create_variant_ids(cr, uid, [product_template_id], context=context)

        # TODO: this is needed to set given values to first variant after creation
        # these fields should be moved to product as lead to confusion
        related_vals = {}
        if vals.get('barcode'):
            related_vals['barcode'] = vals['barcode']
        if vals.get('default_code'):
            related_vals['default_code'] = vals['default_code']
        if vals.get('standard_price'):
            related_vals['standard_price'] = vals['standard_price']
        if vals.get('volume'):
            related_vals['volume'] = vals['volume']
        if vals.get('weight'):
            related_vals['weight'] = vals['weight']
        if related_vals:
            self.write(cr, uid, product_template_id, related_vals, context=context)

        return product_template_id

    def write(self, cr, uid, ids, vals, context=None):
        tools.image_resize_images(vals)
        res = super(product_template, self).write(cr, uid, ids, vals, context=context)
        if 'attribute_line_ids' in vals or vals.get('active'):
            self.create_variant_ids(cr, uid, ids, context=context)
        if 'active' in vals and not vals.get('active'):
            ctx = context and context.copy() or {}
            ctx.update(active_test=False)
            product_ids = []
            for product in self.browse(cr, uid, ids, context=ctx):
                product_ids += map(int, product.product_variant_ids)
            self.pool.get("product.product").write(cr, uid, product_ids, {'active': vals.get('active')}, context=ctx)
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        template = self.browse(cr, uid, id, context=context)
        default['name'] = _("%s (copy)") % (template['name'])
        return super(product_template, self).copy(cr, uid, id, default=default, context=context)

    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'product.template', context=c),
        'list_price': 1,
        'standard_price': 0.0,
        'sale_ok': 1,
        'uom_id': _get_uom_id,
        'uom_po_id': _get_uom_id,
        'categ_id' : _default_category,
        'type' : 'consu',
        'active': True,
        'sequence': 1,
    }

    def _check_uom(self, cursor, user, ids, context=None):
        for product in self.browse(cursor, user, ids, context=context):
            if product.uom_id.category_id.id != product.uom_po_id.category_id.id:
                return False
        return True

    _constraints = [
        (_check_uom, 'Error: The default Unit of Measure and the purchase Unit of Measure must be in the same category.', ['uom_id', 'uom_po_id']),
    ]

    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if 'partner_id' in context:
            pass
        return super(product_template, self).name_get(cr, user, ids, context)

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        # Only use the product.product heuristics if there is a search term and the domain
        # does not specify a match on `product.template` IDs.
        if not name or any(term[0] == 'id' for term in (args or [])):
            return super(product_template, self).name_search(
                cr, user, name=name, args=args, operator=operator, context=context, limit=limit)
        template_ids = set()
        product_product = self.pool['product.product']
        results = product_product.name_search(cr, user, name, args, operator=operator, context=context, limit=limit)
        product_ids = [p[0] for p in results]
        for p in product_product.browse(cr, user, product_ids, context=context):
            template_ids.add(p.product_tmpl_id.id)
        while (results and len(template_ids) < limit):
            domain = [('product_tmpl_id', 'not in', list(template_ids))]
            args = args if args is not None else []
            results = product_product.name_search(
                cr, user, name, args+domain, operator=operator, context=context, limit=limit)
            product_ids = [p[0] for p in results]
            for p in product_product.browse(cr, user, product_ids, context=context):
                template_ids.add(p.product_tmpl_id.id)


        # re-apply product.template order + name_get
        return super(product_template, self).name_search(
            cr, user, '', args=[('id', 'in', list(template_ids))],
            operator='ilike', context=context, limit=limit)

class product_product(osv.osv):
    _name = "product.product"
    _description = "Product"
    _inherits = {'product.template': 'product_tmpl_id'}
    _inherit = ['mail.thread']
    _order = 'default_code,name_template'

    def _product_price(self, cr, uid, ids, name, arg, context=None):
        plobj = self.pool.get('product.pricelist')
        res = {}
        if context is None:
            context = {}
        quantity = context.get('quantity') or 1.0
        pricelist = context.get('pricelist', False)
        partner = context.get('partner', False)
        if pricelist:
            # Support context pricelists specified as display_name or ID for compatibility
            if isinstance(pricelist, basestring):
                pricelist_ids = plobj.name_search(
                    cr, uid, pricelist, operator='=', context=context, limit=1)
                pricelist = pricelist_ids[0][0] if pricelist_ids else pricelist

            if isinstance(pricelist, (int, long)):
                products = self.browse(cr, uid, ids, context=context)
                qtys = map(lambda x: (x, quantity, partner), products)
                pl = plobj.browse(cr, uid, pricelist, context=context)
                price = plobj._price_get_multi(cr,uid, pl, qtys, context=context)
                for id in ids:
                    res[id] = price.get(id, 0.0)
        for id in ids:
            res.setdefault(id, 0.0)
        return res

    def open_product_template(self, cr, uid, ids, context=None):
        """ Utility method used to add an "Open Template" button in product views """
        product_product = self.browse(cr, uid, ids[0], context=context)
        return {'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'view_mode': 'form',
                'res_id': product_product.product_tmpl_id.id,
                'target': 'current',
                'flags': {'form': {'action_buttons': True}}}

    def view_header_get(self, cr, uid, view_id, view_type, context=None):
        if context is None:
            context = {}
        res = super(product_product, self).view_header_get(cr, uid, view_id, view_type, context)
        if (context.get('categ_id', False)):
            return _('Products: ') + self.pool.get('product.category').browse(cr, uid, context['categ_id'], context=context).name
        return res

    def _product_lst_price(self, cr, uid, ids, name, arg, context=None):
        product_uom_obj = self.pool.get('product.uom')
        res = dict.fromkeys(ids, 0.0)

        for product in self.browse(cr, uid, ids, context=context):
            if 'uom' in context:
                uom = product.uom_id
                res[product.id] = product_uom_obj._compute_price(cr, uid,
                        uom.id, product.list_price, context['uom'])
            else:
                res[product.id] = product.list_price
            res[product.id] =  res[product.id] + product.price_extra

        return res

    def _set_product_lst_price(self, cr, uid, id, name, value, args, context=None):
        product_uom_obj = self.pool.get('product.uom')

        product = self.browse(cr, uid, id, context=context)
        if 'uom' in context:
            uom = product.uom_id
            value = product_uom_obj._compute_price(cr, uid,
                    context['uom'], value, uom.id)
        value =  value - product.price_extra
        
        return product.write({'list_price': value})

    def _get_partner_code_name(self, cr, uid, ids, product, partner_id, context=None):
        for supinfo in product.seller_ids:
            if supinfo.name.id == partner_id:
                return {'code': supinfo.product_code or product.default_code, 'name': supinfo.product_name or product.name}
        res = {'code': product.default_code, 'name': product.name}
        return res

    def _product_code(self, cr, uid, ids, name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for p in self.browse(cr, uid, ids, context=context):
            res[p.id] = self._get_partner_code_name(cr, uid, [], p, context.get('partner_id', None), context=context)['code']
        return res

    def _product_partner_ref(self, cr, uid, ids, name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for p in self.browse(cr, uid, ids, context=context):
            data = self._get_partner_code_name(cr, uid, [], p, context.get('partner_id', None), context=context)
            if not data['code']:
                data['code'] = p.code
            if not data['name']:
                data['name'] = p.name
            res[p.id] = (data['code'] and ('['+data['code']+'] ') or '') + (data['name'] or '')
        return res

    def _is_product_variant_impl(self, cr, uid, ids, name, arg, context=None):
        return dict.fromkeys(ids, True)

    def _get_name_template_ids(self, cr, uid, ids, context=None):
        template_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id', 'in', ids)])
        return list(set(template_ids))

    def _get_image_variant(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            if context.get('bin_size'):
                result[obj.id] = obj.image_variant
            else:
                result[obj.id] = tools.image_get_resized_images(obj.image_variant, return_big=True, avoid_resize_medium=True)[name]
            if not result[obj.id]:
                result[obj.id] = getattr(obj.product_tmpl_id, name)
        return result

    def _set_image_variant(self, cr, uid, id, name, value, args, context=None):
        image = tools.image_resize_image_big(value)

        product = self.browse(cr, uid, id, context=context)
        if product.product_tmpl_id.image:
            product.image_variant = image
        else:
            product.product_tmpl_id.image = image

    def _get_price_extra(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for product in self.browse(cr, uid, ids, context=context):
            price_extra = 0.0
            for variant_id in product.attribute_value_ids:
                for price_id in variant_id.price_ids:
                    if price_id.product_tmpl_id.id == product.product_tmpl_id.id:
                        price_extra += price_id.price_extra
            result[product.id] = price_extra
        return result

    def _select_seller(self, cr, uid, product_id, partner_id=False, quantity=0.0, date=time.strftime(DEFAULT_SERVER_DATE_FORMAT), uom_id=False, context=None):
        if context is None:
            context = {}
        res = self.pool.get('product.supplierinfo').browse(cr, uid, [])
        for seller in product_id.seller_ids:
            # Set quantity in UoM of seller
            quantity_uom_seller = quantity
            if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
                quantity_uom_seller = uom_id._compute_qty_obj(uom_id, quantity_uom_seller, seller.product_uom)

            if seller.date_start and seller.date_start > date:
                continue
            if seller.date_end and seller.date_end < date:
                continue
            if partner_id and seller.name not in [partner_id, partner_id.parent_id]:
                continue
            if quantity_uom_seller < seller.qty:
                continue
            if seller.product_id and seller.product_id != product_id:
                continue

            res |= seller
            break
        return res

    _columns = {
        'price': fields.function(_product_price, fnct_inv=_set_product_lst_price, type='float', string='Price', digits_compute=dp.get_precision('Product Price')),
        'price_extra': fields.function(_get_price_extra, type='float', string='Variant Extra Price', help="This is the sum of the extra price of all attributes", digits_compute=dp.get_precision('Product Price')),
        'lst_price': fields.function(_product_lst_price, fnct_inv=_set_product_lst_price, type='float', string='Sale Price', digits_compute=dp.get_precision('Product Price')),
        'code': fields.function(_product_code, type='char', string='Internal Reference'),
        'partner_ref' : fields.function(_product_partner_ref, type='char', string='Customer ref'),
        'default_code' : fields.char('Internal Reference', select=True),
        'active': fields.boolean('Active', help="If unchecked, it will allow you to hide the product without removing it."),
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', required=True, ondelete="cascade", select=True, auto_join=True),
        'barcode': fields.char('Barcode', help="International Article Number used for product identification.", oldname='ean13', copy=False),
        'name_template': fields.related('product_tmpl_id', 'name', string="Template Name", type='char', store={
            'product.template': (_get_name_template_ids, ['name'], 10),
            'product.product': (lambda self, cr, uid, ids, c=None: ids, [], 10),
        }, select=True),
        'attribute_value_ids': fields.many2many('product.attribute.value', id1='prod_id', id2='att_id', string='Attributes', ondelete='restrict'),
        'is_product_variant': fields.function( _is_product_variant_impl, type='boolean', string='Is a product variant'),
        # image: all image fields are base64 encoded and PIL-supported
        'image_variant': fields.binary("Variant Image", attachment=True,
            help="This field holds the image used as image for the product variant, limited to 1024x1024px."),

        'image': fields.function(_get_image_variant, fnct_inv=_set_image_variant,
            string="Big-sized image", type="binary",
            help="Image of the product variant (Big-sized image of product template if false). It is automatically "\
                 "resized as a 1024x1024px image, with aspect ratio preserved."),
        'image_small': fields.function(_get_image_variant, fnct_inv=_set_image_variant,
            string="Small-sized image", type="binary",
            help="Image of the product variant (Small-sized image of product template if false)."),
        'image_medium': fields.function(_get_image_variant, fnct_inv=_set_image_variant,
            string="Medium-sized image", type="binary",
            help="Image of the product variant (Medium-sized image of product template if false)."),
        'standard_price': fields.property(type = 'float', digits_compute=dp.get_precision('Product Price'), 
                                          help="Cost of the product template used for standard stock valuation in accounting and used as a base price on purchase orders. "
                                               "Expressed in the default unit of measure of the product.",
                                          groups="base.group_user", string="Cost"),
        'volume': fields.float('Volume', help="The volume in m3."),
        'weight': fields.float('Gross Weight', digits_compute=dp.get_precision('Stock Weight'), help="The weight of the contents in Kg, not including any packaging, etc."),
    }

    _defaults = {
        'active': 1,
        'color': 0,
    }

    def _check_attribute_value_ids(self, cr, uid, ids, context=None):
        for product in self.browse(cr, uid, ids, context=context):
            attributes = set()
            for value in product.attribute_value_ids:
                if value.attribute_id in attributes:
                    return False
                else:
                    attributes.add(value.attribute_id)
        return True

    _constraints = [
        (_check_attribute_value_ids, 'Error! It is not allowed to choose more than one value for a given attribute.', ['attribute_value_ids'])
    ]

    _sql_constraints = [
        ('barcode_uniq', 'unique(barcode)', _("A barcode can only be assigned to one product !")),
    ]

    def unlink(self, cr, uid, ids, context=None):
        unlink_ids = []
        unlink_product_tmpl_ids = []
        for product in self.browse(cr, uid, ids, context=context):
            # Check if product still exists, in case it has been unlinked by unlinking its template
            if not product.exists():
                continue
            tmpl_id = product.product_tmpl_id.id
            # Check if the product is last product of this template
            other_product_ids = self.search(cr, uid, [('product_tmpl_id', '=', tmpl_id), ('id', '!=', product.id)], context=context)
            if not other_product_ids:
                unlink_product_tmpl_ids.append(tmpl_id)
            unlink_ids.append(product.id)
        res = super(product_product, self).unlink(cr, uid, unlink_ids, context=context)
        # delete templates after calling super, as deleting template could lead to deleting
        # products due to ondelete='cascade'
        self.pool.get('product.template').unlink(cr, uid, unlink_product_tmpl_ids, context=context)
        return res

    def onchange_type(self, cr, uid, ids, type, context=None):
        return {'value': {}}

    def onchange_uom(self, cursor, user, ids, uom_id, uom_po_id):
        if uom_id and uom_po_id:
            uom_obj=self.pool.get('product.uom')
            uom=uom_obj.browse(cursor,user,[uom_id])[0]
            uom_po=uom_obj.browse(cursor,user,[uom_po_id])[0]
            if uom.category_id.id != uom_po.category_id.id:
                return {'value': {'uom_po_id': uom_id}}
        return False

    def on_order(self, cr, uid, ids, orderline, quantity):
        pass

    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []

        def _name_get(d):
            name = d.get('name','')
            code = context.get('display_default_code', True) and d.get('default_code',False) or False
            if code:
                name = '[%s] %s' % (code,name)
            return (d['id'], name)

        partner_id = context.get('partner_id', False)
        if partner_id:
            partner_ids = [partner_id, self.pool['res.partner'].browse(cr, user, partner_id, context=context).commercial_partner_id.id]
        else:
            partner_ids = []

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights(cr, user, "read")
        self.check_access_rule(cr, user, ids, "read", context=context)

        result = []
        for product in self.browse(cr, SUPERUSER_ID, ids, context=context):
            variant = ", ".join([v.name for v in product.attribute_value_ids])
            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = []
            if partner_ids:
                if variant:
                    sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and (x.product_id == product)]
                if not sellers:
                    sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and not x.product_id]
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    mydict = {
                              'id': product.id,
                              'name': seller_variant or name,
                              'default_code': s.product_code or product.default_code,
                              }
                    temp = _name_get(mydict)
                    if temp not in result:
                        result.append(temp)
            else:
                mydict = {
                          'id': product.id,
                          'name': name,
                          'default_code': product.default_code,
                          }
                result.append(_name_get(mydict))
        return result

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if context is None:
            context = {}
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            ids = []
            if operator in positive_operators:
                ids = self.search(cr, user, [('default_code','=',name)]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('barcode','=',name)]+ args, limit=limit, context=context)
            if not ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                ids = self.search(cr, user, args + [('default_code', operator, name)], limit=limit, context=context)
                if not limit or len(ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(ids)) if limit else False
                    ids += self.search(cr, user, args + [('name', operator, name), ('id', 'not in', ids)], limit=limit2, context=context)
            elif not ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                ids = self.search(cr, user, args + ['&', ('default_code', operator, name), ('name', operator, name)], limit=limit, context=context)
            if not ids and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user, [('default_code','=', res.group(2))] + args, limit=limit, context=context)
            # still no results, partner in context: search on supplier info as last hope to find something
            if not ids and context.get('partner_id'):
                supplier_ids = self.pool['product.supplierinfo'].search(
                    cr, user, [
                        ('name', '=', context.get('partner_id')),
                        '|',
                        ('product_code', operator, name),
                        ('product_name', operator, name)
                    ], context=context)
                if supplier_ids:
                    ids = self.search(cr, user, [('product_tmpl_id.seller_ids', 'in', supplier_ids)], limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result

    #
    # Could be overrided for variants matrices prices
    #
    def price_get(self, cr, uid, ids, ptype='list_price', context=None):
        products = self.browse(cr, uid, ids, context=context)
        return self.pool.get("product.template")._price_get(cr, uid, products, ptype=ptype, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context={}

        if default is None:
            default = {}

        product = self.browse(cr, uid, id, context)
        if context.get('variant'):
            # if we copy a variant or create one, we keep the same template
            default['product_tmpl_id'] = product.product_tmpl_id.id
        elif 'name' not in default:
            default['name'] = _("%s (copy)") % (product.name,)

        return super(product_product, self).copy(cr, uid, id, default=default, context=context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if context.get('search_default_categ_id'):
            args.append((('categ_id', 'child_of', context['search_default_categ_id'])))
        return super(product_product, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

    def open_product_template(self, cr, uid, ids, context=None):
        """ Utility method used to add an "Open Template" button in product views """
        product = self.browse(cr, uid, ids[0], context=context)
        return {'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'view_mode': 'form',
                'res_id': product.product_tmpl_id.id,
                'target': 'new'}

    def create(self, cr, uid, vals, context=None):
        ctx = dict(context or {}, create_product_product=True)
        product_id = super(product_product, self).create(cr, uid, vals, context=ctx)
        self._set_standard_price(cr, uid, product_id, vals.get('standard_price', 0.0), context=context)
        return product_id

    def write(self, cr, uid, ids, vals, context=None):
        ''' Store the standard price change in order to be able to retrieve the cost of a product for a given date'''
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(product_product, self).write(cr, uid, ids, vals, context=context)
        if 'standard_price' in vals:
            for product_id in ids:
                self._set_standard_price(cr, uid, product_id, vals['standard_price'], context=context)
        return res

    def _set_standard_price(self, cr, uid, product_id, value, context=None):
        ''' Store the standard price change in order to be able to retrieve the cost of a product for a given date'''
        if context is None:
            context = {}
        price_history_obj = self.pool['product.price.history']
        user_company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        company_id = context.get('force_company', user_company)
        price_history_obj.create(cr, uid, {
            'product_id': product_id,
            'cost': value,
            'company_id': company_id,
        }, context=context)

    def get_history_price(self, cr, uid, product_id, company_id, date=None, context=None):
        if context is None:
            context = {}
        if date is None:
            date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        price_history_obj = self.pool.get('product.price.history')
        history_ids = price_history_obj.search(cr, uid, [('company_id', '=', company_id), ('product_id', '=', product_id), ('datetime', '<=', date)], limit=1)
        if history_ids:
            return price_history_obj.read(cr, uid, history_ids[0], ['cost'], context=context)['cost']
        return 0.0

    def _need_procurement(self, cr, uid, ids, context=None):
        # When sale/product is installed alone, there is no need to create procurements. Only
        # sale_stock and sale_service need procurements
        return False

class product_packaging(osv.osv):
    _name = "product.packaging"
    _description = "Packaging"
    _order = 'sequence'
    _columns = {
        'name' : fields.char('Packaging Type', required=True),
        'sequence': fields.integer('Sequence', help="The first in the sequence is the default one."),
        'product_tmpl_id': fields.many2one('product.template', string='Product'),
        'qty' : fields.float('Quantity by Package',
            help="The total number of products you can put by pallet or box."),
    }
    _defaults = {
        'sequence' : 1,
    }


class product_supplierinfo(osv.osv):
    _name = "product.supplierinfo"
    _description = "Information about a product vendor"
    _order = 'sequence, min_qty desc, price'

    def _calc_qty(self, cr, uid, ids, fields, arg, context=None):
        result = {}
        for supplier_info in self.browse(cr, uid, ids, context=context):
            for field in fields:
                result[supplier_info.id] = {field:False}
            qty = supplier_info.min_qty
            result[supplier_info.id]['qty'] = qty
        return result

    _columns = {
        'name': fields.many2one('res.partner', 'Vendor', required=True, domain=[('supplier', '=', True)], ondelete='cascade', help="Vendor of this product"),
        'product_name': fields.char('Vendor Product Name', help="This vendor's product name will be used when printing a request for quotation. Keep empty to use the internal one."),
        'product_code': fields.char('Vendor Product Code', help="This vendor's product code will be used when printing a request for quotation. Keep empty to use the internal one."),
        'sequence': fields.integer('Sequence', help="Assigns the priority to the list of product vendor."),
        'product_uom': fields.related('product_tmpl_id', 'uom_po_id', type='many2one', relation='product.uom', string="Vendor Unit of Measure", readonly="1", help="This comes from the product form."),
        'min_qty': fields.float('Minimal Quantity', required=True, help="The minimal quantity to purchase from this vendor, expressed in the vendor Product Unit of Measure if not any, in the default unit of measure of the product otherwise."),
        'qty': fields.function(_calc_qty, store=True, type='float', string='Quantity', multi="qty", help="This is a quantity which is converted into Default Unit of Measure."),
        'price': fields.float('Price', required=True, digits_compute=dp.get_precision('Product Price'), help="The price to purchase a product"),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'date_start': fields.date('Start Date', help="Start date for this vendor price"),
        'date_end': fields.date('End Date', help="End date for this vendor price"),
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', ondelete='cascade', select=True, oldname='product_id'),
        'delay': fields.integer('Delivery Lead Time', required=True, help="Lead time in days between the confirmation of the purchase order and the receipt of the products in your warehouse. Used by the scheduler for automatic computation of the purchase order planning."),
        'company_id': fields.many2one('res.company', string='Company', select=1),
        'product_id': fields.many2one('product.product', string='Product Variant', help="When this field is filled in, the vendor data will only apply to the variant."),
    }
    _defaults = {
        'min_qty': 0.0,
        'sequence': 1,
        'delay': 1,
        'price': 0.0,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'product.supplierinfo', context=c),
        'currency_id': lambda self, cr, uid, context: self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.currency_id.id,
    }


class res_currency(osv.osv):
    _inherit = 'res.currency'

    def _check_main_currency_rounding(self, cr, uid, ids, context=None):
        cr.execute('SELECT digits FROM decimal_precision WHERE name like %s',('Account',))
        digits = cr.fetchone()
        if digits and len(digits):
            digits = digits[0]
            main_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id
            for currency_id in ids:
                if currency_id == main_currency.id:
                    if float_compare(main_currency.rounding, 10 ** -digits, precision_digits=6) == -1:
                        return False
        return True

    _constraints = [
        (_check_main_currency_rounding, 'Error! You cannot define a rounding factor for the company\'s main currency that is smaller than the decimal precision of \'Account\'.', ['rounding']),
    ]

class decimal_precision(osv.osv):
    _inherit = 'decimal.precision'

    def _check_main_currency_rounding(self, cr, uid, ids, context=None):
        cr.execute('SELECT id, digits FROM decimal_precision WHERE name like %s',('Account',))
        res = cr.fetchone()
        if res and len(res):
            account_precision_id, digits = res
            main_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id
            for decimal_precision in ids:
                if decimal_precision == account_precision_id:
                    if float_compare(main_currency.rounding, 10 ** -digits, precision_digits=6) == -1:
                        return False
        return True

    _constraints = [
        (_check_main_currency_rounding, 'Error! You cannot define the decimal precision of \'Account\' as greater than the rounding factor of the company\'s main currency', ['digits']),
    ]
