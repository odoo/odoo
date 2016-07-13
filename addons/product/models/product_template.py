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
            help='A stockable product is a product for which you manage stock. The "Inventory" app has to be installed.\n'
                 'A consumable product, on the other hand, is a product for which stock is not managed.\n'
                 'A service is a non-material product you provide.\n'
                 'A digital content is a non-material product you sell online. The files attached to the products are the one that are sold on '
                 'the e-commerce such as e-books, music, pictures,... The "Digital Product" module has to be installed.'),
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
        'weight': fields.function(_compute_product_template_field, fnct_inv=_set_product_template_field, multi='_compute_product_template_field', type='float', string='Weight', digits_compute=dp.get_precision('Stock Weight'), help="The weight of the contents in Kg, not including any packaging, etc.", store={
            _name: (lambda s,c,u,i,t: i, ['product_variant_ids'], 10),
            'product.product': (_get_template_id_from_product, ['product_tmpl_id', 'weight'], 10),
        }),
        'warranty': fields.float('Warranty'),
        'sale_ok': fields.boolean('Can be Sold', help="Specify if the product can be selected in a sales order line."),
        'pricelist_id': fields.dummy(string='Pricelist', relation='product.pricelist', type='many2one'),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True, help="Default Unit of Measure used for all stock operation."),
        'uom_po_id': fields.many2one('product.uom', 'Purchase Unit of Measure', required=True, help="Default Unit of Measure used for purchase orders. It must be in the same category than the default unit of measure."),
        'company_id': fields.many2one('res.company', 'Company', select=1),
        'packaging_ids': fields.one2many(
            'product.packaging', 'product_tmpl_id', 'Logistical Units',
            help="Gives the different ways to package the same product. This has no impact on "
                 "the picking order and is mainly used if you use the EDI module."),
        'seller_ids': fields.one2many('product.supplierinfo', 'product_tmpl_id', 'Vendors'),

        'active': fields.boolean('Active', help="If unchecked, it will allow you to hide the product without removing it."),
        'color': fields.integer('Color Index'),
        'is_product_variant': fields.function(_is_product_variant, type='boolean', string='Is a product variant'),

        'attribute_line_ids': fields.one2many('product.attribute.line', 'product_tmpl_id', 'Product Attributes'),
        'product_variant_ids': fields.one2many('product.product', 'product_tmpl_id', 'Products', required=True),
        'product_variant_count': fields.function(_get_product_variant_count, type='integer', string='# of Product Variants'),

        # related to display product product information if is_product_variant
        'barcode': fields.related('product_variant_ids', 'barcode', type='char', string='Barcode', oldname='ean13'),
        'default_code': fields.function(_compute_product_template_field, fnct_inv=_set_product_template_field, multi='_compute_product_template_field', type='char', string='Internal Reference', store={
            _name: (lambda s,c,u,i,t: i, ['product_variant_ids'], 10),
            'product.product': (_get_template_id_from_product, ['product_tmpl_id', 'default_code'], 10),
        }),

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
        if 'name' not in default:
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

    def name_get(self, cr, uid, ids, context=None):
        return [(product.id, '%s%s' % (product.default_code and '[%s] ' % product.default_code or '', product.name))
                for product in self.browse(cr, uid, ids, context=context)]

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
