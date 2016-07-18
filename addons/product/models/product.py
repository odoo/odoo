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

    def _compute_product_count(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        prod_templates = self.pool['product.template'].read_group(cr, uid, [('categ_id', 'in', ids)], ['categ_id'], ['categ_id'], context=context)
        for prod_template in prod_templates:
            res[prod_template['categ_id'][0]] = prod_template['categ_id_count']
        return res

    _name = "product.category"
    _description = "Product Category"
    _columns = {
        'name': fields.char('Name', required=True, translate=True, select=True),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Name'),
        'parent_id': fields.many2one('product.category','Parent Category', select=True, ondelete='cascade'),
        'child_id': fields.one2many('product.category', 'parent_id', string='Child Categories'),
        'type': fields.selection([('view','View'), ('normal','Normal')], 'Category Type', help="A category of the view type is a virtual category that can be used as the parent of another category to create a hierarchical structure."),
        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),
        'product_count': fields.function(_compute_product_count, type="integer", help="The number of products under this category (Does not consider the children categories)"),
    }


    _defaults = {
        'type' : 'normal',
    }

    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
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
        'cost': fields.float('Cost', digits_compute=dp.get_precision('Product Price')),
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
# Products
#----------------------------------------------------------


class product_product(osv.osv):
    _name = "product.product"
    _description = "Product"
    _inherits = {'product.template': 'product_tmpl_id'}
    _inherit = ['mail.thread']
    _order = 'default_code'

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
                quantities = [quantity] * len(products)
                partners = [partner] * len(products)
                pl = plobj.browse(cr, uid, pricelist, context=context)
                price = plobj.get_products_price(cr, uid, [pl.id], products, quantities, partners, context=context)
                for id in ids:
                    res[id] = price.get(id, 0.0)
        for id in ids:
            res.setdefault(id, 0.0)
        return res

    def view_header_get(self, cr, uid, view_id, view_type, context=None):
        if context is None:
            context = {}
        res = super(product_product, self).view_header_get(cr, uid, view_id, view_type, context)
        if (context.get('categ_id', False)):
            return _('Products: ') + self.pool.get('product.category').browse(cr, uid, context['categ_id'], context=context).name
        return res

    def _product_lst_price(self, cr, uid, ids, name, arg, context=None):
        product_uom_obj = self.pool.get('product.uom')
        if 'uom' in context:
            to_uom = self.pool['product.uom'].browse(cr, uid, context['uom'], context=context)
        res = dict.fromkeys(ids, 0.0)

        for product in self.browse(cr, uid, ids, context=context):
            if 'uom' in context:
                uom = product.uom_id
                res[product.id] = product_uom_obj._compute_price(cr, uid,
                        [uom.id], product.list_price, to_uom)
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
                    [context['uom']], value, uom)
        value =  value - product.price_extra
        
        return product.write({'list_price': value})

    def _get_partner_code_name(self, cr, uid, ids, partner_id, context=None):
        product = self.browse(cr, uid, ids[0], context=context)
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
            res[p.id] = self._get_partner_code_name(cr, uid, [p.id], context.get('partner_id', None), context=context)['code']
        return res

    def _product_partner_ref(self, cr, uid, ids, name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for p in self.browse(cr, uid, ids, context=context):
            data = self._get_partner_code_name(cr, uid, [p.id], context.get('partner_id', None), context=context)
            if not data['code']:
                data['code'] = p.code
            if not data['name']:
                data['name'] = p.name
            res[p.id] = (data['code'] and ('['+data['code']+'] ') or '') + (data['name'] or '')
        return res

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

    def _select_seller(self, cr, uid, ids, partner_id=False, quantity=0.0, date=time.strftime(DEFAULT_SERVER_DATE_FORMAT), uom_id=False, context=None):
        if context is None:
            context = {}
        res = self.pool.get('product.supplierinfo').browse(cr, uid, [])
        product = self.browse(cr, uid, ids[0], context=context)
        for seller in product.seller_ids:
            # Set quantity in UoM of seller
            quantity_uom_seller = quantity
            if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
                quantity_uom_seller = uom_id._compute_quantity(quantity_uom_seller, seller.product_uom)

            if seller.date_start and seller.date_start > date:
                continue
            if seller.date_end and seller.date_end < date:
                continue
            if partner_id and seller.name not in [partner_id, partner_id.parent_id]:
                continue
            if quantity_uom_seller < seller.qty:
                continue
            if seller.product_id and seller.product_id != product:
                continue

            res |= seller
            break
        return res

    def _get_pricelist_items(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for prod in self.browse(cr, uid, ids, context=context):
            item_ids = self.pool['product.pricelist.item'].search(cr, uid, ['|', ('product_id', '=', prod.id), ('product_tmpl_id', '=', prod.product_tmpl_id.id)], context=context)
            res[prod.id] = item_ids
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
        'attribute_value_ids': fields.many2many('product.attribute.value', id1='prod_id', id2='att_id', string='Attributes', ondelete='restrict'),
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
        'weight': fields.float('Weight', digits_compute=dp.get_precision('Stock Weight'), help="The weight of the contents in Kg, not including any packaging, etc."),
        'pricelist_item_ids': fields.function(_get_pricelist_items, type='many2many', relation='product.pricelist.item', string='Pricelist Items'),
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

    def onchange_uom(self, cr, uid, ids, uom_id, uom_po_id, context=None):
        if uom_id and uom_po_id:
            uom_obj = self.pool.get('product.uom')
            uom = uom_obj.browse(cr, uid, [uom_id], context=context)[0]
            uom_po = uom_obj.browse(cr, uid, [uom_po_id], context=context)[0]
            if uom.category_id.id != uom_po.category_id.id:
                return {'value': {'uom_po_id': uom_id}}
        return False

    def name_get(self, cr, uid, ids, context=None):
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
            partner_ids = [partner_id, self.pool['res.partner'].browse(cr, uid, partner_id, context=context).commercial_partner_id.id]
        else:
            partner_ids = []

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights(cr, uid, "read")
        self.check_access_rule(cr, uid, ids, "read", context=context)

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

    def name_search(self, cr, uid, name='', args=None, operator='ilike', context=None, limit=100):
        if context is None:
            context = {}
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            ids = []
            if operator in positive_operators:
                ids = self.search(cr, uid, [('default_code','=',name)]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, uid, [('barcode','=',name)]+ args, limit=limit, context=context)
            if not ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                ids = self.search(cr, uid, args + [('default_code', operator, name)], limit=limit, context=context)
                if not limit or len(ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(ids)) if limit else False
                    ids += self.search(cr, uid, args + [('name', operator, name), ('id', 'not in', ids)], limit=limit2, context=context)
            elif not ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                ids = self.search(cr, uid, args + ['&', ('default_code', operator, name), ('name', operator, name)], limit=limit, context=context)
            if not ids and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, uid, [('default_code','=', res.group(2))] + args, limit=limit, context=context)
            # still no results, partner in context: search on supplier info as last hope to find something
            if not ids and context.get('partner_id'):
                supplier_ids = self.pool['product.supplierinfo'].search(
                    cr, uid, [
                        ('name', '=', context.get('partner_id')),
                        '|',
                        ('product_code', operator, name),
                        ('product_name', operator, name)
                    ], context=context)
                if supplier_ids:
                    ids = self.search(cr, uid, [('product_tmpl_id.seller_ids', 'in', supplier_ids)], limit=limit, context=context)
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        result = self.name_get(cr, uid, ids, context=context)
        return result

    @api.multi
    def price_compute(self, price_type, uom=False, currency=False, company=False):
        # TDE FIXME: delegate to template or not ? fields are reencoded here ...
        # compatibility about context keys used a bit everywhere in the code
        if not uom and self._context.get('uom'):
            uom = self.env['product.uom'].browse(self._context['uom'])
        if not currency and self._context.get('currency'):
            currency = self.env['res.currency'].browse(self._context['currency'])

        products = self
        if price_type == 'standard_price':
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            products = self.with_context(force_company=company and company.id or self._context.get('force_company', self.env.user.company_id.id)).sudo()

        prices = dict.fromkeys(self.ids, 0.0)
        for product in products:
            prices[product.id] = product[price_type] or 0.0
            if price_type == 'list_price':
                prices[product.id] += product.price_extra

            if uom:
                prices[product.id] = product.uom_id._compute_price(prices[product.id], uom)

            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                prices[product.id] = product.currency_id.compute(prices[product.id], currency)

        return prices


    # compatibility to remove after v10 - DEPRECATED
    def price_get(self, cr, uid, ids, ptype='list_price', context=None):
        return self.browse(cr, uid, ids, context=context).price_compute(ptype)

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
            default['name'] = product.name

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
        self._set_standard_price(cr, uid, [product_id], vals.get('standard_price', 0.0), context=context)
        return product_id

    def write(self, cr, uid, ids, vals, context=None):
        ''' Store the standard price change in order to be able to retrieve the cost of a product for a given date'''
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(product_product, self).write(cr, uid, ids, vals, context=context)
        if 'standard_price' in vals:
            self._set_standard_price(cr, uid, ids, vals['standard_price'], context=context)
        return res

    def _set_standard_price(self, cr, uid, ids, value, context=None):
        ''' Store the standard price change in order to be able to retrieve the cost of a product for a given date'''
        if context is None:
            context = {}
        price_history_obj = self.pool['product.price.history']
        user_company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        company_id = context.get('force_company', user_company)
        for product_id in ids:
            price_history_obj.create(cr, uid, {
                'product_id': product_id,
                'cost': value,
                'company_id': company_id,
            }, context=context)

    def get_history_price(self, cr, uid, ids, company_id, date=None, context=None):
        if context is None:
            context = {}
        if date is None:
            date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        price_history_obj = self.pool.get('product.price.history')
        history_ids = price_history_obj.search(cr, uid, [('company_id', '=', company_id), ('product_id', 'in', ids), ('datetime', '<=', date)], limit=1)
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
        'qty' : fields.float('Quantity per Package',
            help="The total number of products you can have per pallet or box."),
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
