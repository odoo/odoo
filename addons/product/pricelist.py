# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from itertools import chain
import time

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import except_orm

import openerp.addons.decimal_precision as dp


class price_type(osv.osv):
    """
        The price type is used to points which field in the product form
        is a price and in which currency is this price expressed.
        When a field is a price, you can use it in pricelists to base
        sale and purchase prices based on some fields of the product.
    """
    def _price_field_get(self, cr, uid, context=None):
        mf = self.pool.get('ir.model.fields')
        ids = mf.search(cr, uid, [('model','in', (('product.product'),('product.template'))), ('ttype','=','float')], context=context)
        res = []
        for field in mf.browse(cr, uid, ids, context=context):
            if not (field.name, field.field_description) in res:
                res.append((field.name, field.field_description))
        return res

    def _get_field_currency(self, cr, uid, fname, ctx):
        ids = self.search(cr, uid, [('field','=',fname)], context=ctx)
        return self.browse(cr, uid, ids, context=ctx)[0].currency_id

    def _get_currency(self, cr, uid, ctx):
        comp = self.pool.get('res.users').browse(cr,uid,uid).company_id
        if not comp:
            comp_id = self.pool.get('res.company').search(cr, uid, [])[0]
            comp = self.pool.get('res.company').browse(cr, uid, comp_id)
        return comp.currency_id.id

    _name = "product.price.type"
    _description = "Price Type"
    _columns = {
        "name" : fields.char("Price Name", required=True, translate=True, help="Name of this kind of price."),
        "active" : fields.boolean("Active"),
        "field" : fields.selection(_price_field_get, "Product Field", size=32, required=True, help="Associated field in the product form."),
        "currency_id" : fields.many2one('res.currency', "Currency", required=True, help="The currency the field is expressed in."),
    }
    _defaults = {
        "active": lambda *args: True,
        "currency_id": _get_currency
    }


#----------------------------------------------------------
# Price lists
#----------------------------------------------------------

class product_pricelist_type(osv.osv):
    _name = "product.pricelist.type"
    _description = "Pricelist Type"
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'key': fields.char('Key', required=True, help="Used in the code to select specific prices based on the context. Keep unchanged."),
    }


class product_pricelist(osv.osv):
    def _pricelist_type_get(self, cr, uid, context=None):
        pricelist_type_obj = self.pool.get('product.pricelist.type')
        pricelist_type_ids = pricelist_type_obj.search(cr, uid, [], order='name')
        pricelist_types = pricelist_type_obj.read(cr, uid, pricelist_type_ids, ['key','name'], context=context)

        res = []

        for type in pricelist_types:
            res.append((type['key'],type['name']))

        return res

    _name = "product.pricelist"
    _description = "Pricelist"
    _order = 'name'
    _columns = {
        'name': fields.char('Pricelist Name', required=True, translate=True),
        'active': fields.boolean('Active', help="If unchecked, it will allow you to hide the pricelist without removing it."),
        'type': fields.selection(_pricelist_type_get, 'Pricelist Type', required=True),
        'version_id': fields.one2many('product.pricelist.version', 'pricelist_id', 'Pricelist Versions', copy=True),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'company_id': fields.many2one('res.company', 'Company'),
    }

    def name_get(self, cr, uid, ids, context=None):
        result= []
        if not all(ids):
            return result
        for pl in self.browse(cr, uid, ids, context=context):
            name = pl.name + ' ('+ pl.currency_id.name + ')'
            result.append((pl.id,name))
        return result

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if name and operator == '=' and not args:
            # search on the name of the pricelist and its currency, opposite of name_get(),
            # Used by the magic context filter in the product search view.
            query_args = {'name': name, 'limit': limit, 'lang': (context or {}).get('lang') or 'en_US'}
            query = """SELECT p.id
                       FROM ((
                                SELECT pr.id, pr.name
                                FROM product_pricelist pr JOIN
                                     res_currency cur ON 
                                         (pr.currency_id = cur.id)
                                WHERE pr.name || ' (' || cur.name || ')' = %(name)s
                            )
                            UNION (
                                SELECT tr.res_id as id, tr.value as name
                                FROM ir_translation tr JOIN
                                     product_pricelist pr ON (
                                        pr.id = tr.res_id AND
                                        tr.type = 'model' AND
                                        tr.name = 'product.pricelist,name' AND
                                        tr.lang = %(lang)s
                                     ) JOIN
                                     res_currency cur ON 
                                         (pr.currency_id = cur.id)
                                WHERE tr.value || ' (' || cur.name || ')' = %(name)s
                            )
                        ) p
                       ORDER BY p.name"""
            if limit:
                query += " LIMIT %(limit)s"
            cr.execute(query, query_args)
            ids = [r[0] for r in cr.fetchall()]
            # regular search() to apply ACLs - may limit results below limit in some cases
            ids = self.search(cr, uid, [('id', 'in', ids)], limit=limit, context=context)
            if ids:
                return self.name_get(cr, uid, ids, context)
        return super(product_pricelist, self).name_search(
            cr, uid, name, args, operator=operator, context=context, limit=limit)


    def _get_currency(self, cr, uid, ctx):
        comp = self.pool.get('res.users').browse(cr, uid, uid).company_id
        if not comp:
            comp_id = self.pool.get('res.company').search(cr, uid, [])[0]
            comp = self.pool.get('res.company').browse(cr, uid, comp_id)
        return comp.currency_id.id

    _defaults = {
        'active': lambda *a: 1,
        "currency_id": _get_currency
    }

    def price_get_multi(self, cr, uid, ids, products_by_qty_by_partner, context=None):
        return dict((key, dict((key, price[0]) for key, price in value.items())) for key, value in self.price_rule_get_multi(cr, uid, ids, products_by_qty_by_partner, context=context).items())

    def price_rule_get_multi(self, cr, uid, ids, products_by_qty_by_partner, context=None):
        """multi products 'price_get'.
           @param ids:
           @param products_by_qty:
           @param partner:
           @param context: {
             'date': Date of the pricelist (%Y-%m-%d),}
           @return: a dict of dict with product_id as key and a dict 'price by pricelist' as value
        """
        if not ids:
            ids = self.pool.get('product.pricelist').search(cr, uid, [], context=context)
        results = {}
        for pricelist in self.browse(cr, uid, ids, context=context):
            subres = self._price_rule_get_multi(cr, uid, pricelist, products_by_qty_by_partner, context=context)
            for product_id,price in subres.items():
                results.setdefault(product_id, {})
                results[product_id][pricelist.id] = price
        return results

    def _price_get_multi(self, cr, uid, pricelist, products_by_qty_by_partner, context=None):
        return dict((key, price[0]) for key, price in self._price_rule_get_multi(cr, uid, pricelist, products_by_qty_by_partner, context=context).items())

    def _price_rule_get_multi(self, cr, uid, pricelist, products_by_qty_by_partner, context=None):
        context = context or {}
        date = context.get('date') or time.strftime('%Y-%m-%d')
        date = date[0:10]

        products = map(lambda x: x[0], products_by_qty_by_partner)
        currency_obj = self.pool.get('res.currency')
        product_obj = self.pool.get('product.template')
        product_uom_obj = self.pool.get('product.uom')
        price_type_obj = self.pool.get('product.price.type')

        if not products:
            return {}

        version = False
        for v in pricelist.version_id:
            if ((v.date_start is False) or (v.date_start <= date)) and ((v.date_end is False) or (v.date_end >= date)):
                version = v
                break
        if not version:
            raise osv.except_osv(_('Warning!'), _("At least one pricelist has no active version !\nPlease create or activate one."))
        categ_ids = {}
        for p in products:
            categ = p.categ_id
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
        categ_ids = categ_ids.keys()

        is_product_template = products[0]._name == "product.template"
        if is_product_template:
            prod_tmpl_ids = [tmpl.id for tmpl in products]
            # all variants of all products
            prod_ids = [p.id for p in
                        list(chain.from_iterable([t.product_variant_ids for t in products]))]
        else:
            prod_ids = [product.id for product in products]
            prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

        # Load all rules
        cr.execute(
            'SELECT i.id '
            'FROM product_pricelist_item AS i '
            'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = any(%s)) '
                'AND (product_id IS NULL OR (product_id = any(%s))) '
                'AND ((categ_id IS NULL) OR (categ_id = any(%s))) '
                'AND (price_version_id = %s) '
            'ORDER BY sequence, min_quantity desc',
            (prod_tmpl_ids, prod_ids, categ_ids, version.id))
        
        item_ids = [x[0] for x in cr.fetchall()]
        items = self.pool.get('product.pricelist.item').browse(cr, uid, item_ids, context=context)

        price_types = {}

        results = {}
        for product, qty, partner in products_by_qty_by_partner:
            results[product.id] = 0.0
            rule_id = False
            price = False

            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.
            qty_uom_id = context.get('uom') or product.uom_id.id
            price_uom_id = product.uom_id.id
            qty_in_product_uom = qty
            if qty_uom_id != product.uom_id.id:
                try:
                    qty_in_product_uom = product_uom_obj._compute_qty(
                        cr, uid, context['uom'], qty, product.uom_id.id or product.uos_id.id)
                except except_orm:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass

            for rule in items:
                if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
                    continue
                if is_product_template:
                    if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and not (product.product_variant_count == 1 and product.product_variant_ids[0].id == rule.product_id.id):
                        # product rule acceptable on template if has only one variant
                        continue
                else:
                    if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and product.id != rule.product_id.id:
                        continue

                if rule.categ_id:
                    cat = product.categ_id
                    while cat:
                        if cat.id == rule.categ_id.id:
                            break
                        cat = cat.parent_id
                    if not cat:
                        continue

                if rule.base == -1:
                    if rule.base_pricelist_id:
                        price_tmp = self._price_get_multi(cr, uid,
                                rule.base_pricelist_id, [(product,
                                qty, partner)], context=context)[product.id]
                        ptype_src = rule.base_pricelist_id.currency_id.id
                        price_uom_id = qty_uom_id
                        price = currency_obj.compute(cr, uid,
                                ptype_src, pricelist.currency_id.id,
                                price_tmp, round=False,
                                context=context)
                elif rule.base == -2:
                    seller = False
                    for seller_id in product.seller_ids:
                        if (not partner) or (seller_id.name.id != partner):
                            continue
                        seller = seller_id
                    if not seller and product.seller_ids:
                        seller = product.seller_ids[0]
                    if seller:
                        qty_in_seller_uom = qty
                        seller_uom = seller.product_uom.id
                        if qty_uom_id != seller_uom:
                            qty_in_seller_uom = product_uom_obj._compute_qty(cr, uid, qty_uom_id, qty, to_uom_id=seller_uom)
                        price_uom_id = seller_uom
                        for line in seller.pricelist_ids:
                            if line.min_quantity <= qty_in_seller_uom:
                                price = line.price

                else:
                    if rule.base not in price_types:
                        price_types[rule.base] = price_type_obj.browse(cr, uid, int(rule.base))
                    price_type = price_types[rule.base]

                    # price_get returns the price in the context UoM, i.e. qty_uom_id
                    price_uom_id = qty_uom_id
                    price = currency_obj.compute(
                            cr, uid,
                            price_type.currency_id.id, pricelist.currency_id.id,
                            product_obj._price_get(cr, uid, [product], price_type.field, context=context)[product.id],
                            round=False, context=context)

                if price is not False:
                    price_limit = price
                    price = price * (1.0+(rule.price_discount or 0.0))
                    if rule.price_round:
                        price = tools.float_round(price, precision_rounding=rule.price_round)

                    convert_to_price_uom = (lambda price: product_uom_obj._compute_price(
                                                cr, uid, product.uom_id.id,
                                                price, price_uom_id))
                    if rule.price_surcharge:
                        price_surcharge = convert_to_price_uom(rule.price_surcharge)
                        price += price_surcharge

                    if rule.price_min_margin:
                        price_min_margin = convert_to_price_uom(rule.price_min_margin)
                        price = max(price, price_limit + price_min_margin)

                    if rule.price_max_margin:
                        price_max_margin = convert_to_price_uom(rule.price_max_margin)
                        price = min(price, price_limit + price_max_margin)

                    rule_id = rule.id
                break

            # Final price conversion to target UoM
            price = product_uom_obj._compute_price(cr, uid, price_uom_id, price, qty_uom_id)

            results[product.id] = (price, rule_id)
        return results

    def price_get(self, cr, uid, ids, prod_id, qty, partner=None, context=None):
        return dict((key, price[0]) for key, price in self.price_rule_get(cr, uid, ids, prod_id, qty, partner=partner, context=context).items())

    def price_rule_get(self, cr, uid, ids, prod_id, qty, partner=None, context=None):
        product = self.pool.get('product.product').browse(cr, uid, prod_id, context=context)
        res_multi = self.price_rule_get_multi(cr, uid, ids, products_by_qty_by_partner=[(product, qty, partner)], context=context)
        res = res_multi[prod_id]
        return res


class product_pricelist_version(osv.osv):
    _name = "product.pricelist.version"
    _description = "Pricelist Version"

    def _get_product_pricelist(self, cr, uid, ids, context=None):
        result = set()
        for pricelist in self.pool['product.pricelist'].browse(cr, uid, ids, context=context):
            for version_id in pricelist.version_id:
                result.add(version_id.id)
        return list(result)

    _columns = {
        'pricelist_id': fields.many2one('product.pricelist', 'Price List',
            required=True, select=True, ondelete='cascade'),
        'name': fields.char('Name', required=True, translate=True),
        'active': fields.boolean('Active',
            help="When a version is duplicated it is set to non active, so that the " \
            "dates do not overlaps with original version. You should change the dates " \
            "and reactivate the pricelist"),
        'items_id': fields.one2many('product.pricelist.item',
            'price_version_id', 'Price List Items', required=True, copy=True),
        'date_start': fields.date('Start Date', help="First valid date for the version."),
        'date_end': fields.date('End Date', help="Last valid date for the version."),
        'company_id': fields.related('pricelist_id','company_id',type='many2one',
            readonly=True, relation='res.company', string='Company', store={
                'product.pricelist': (_get_product_pricelist, ['company_id'], 20),
                'product.pricelist.version': (lambda self, cr, uid, ids, c=None: ids, ['pricelist_id'], 20),
            })
    }
    _defaults = {
        'active': lambda *a: 1,
    }

    def _check_date(self, cursor, user, ids, context=None):
        for pricelist_version in self.browse(cursor, user, ids, context=context):
            if not pricelist_version.active:
                continue
            where = []
            if pricelist_version.date_start:
                where.append("((date_end>='%s') or (date_end is null))" % (pricelist_version.date_start,))
            if pricelist_version.date_end:
                where.append("((date_start<='%s') or (date_start is null))" % (pricelist_version.date_end,))

            cursor.execute('SELECT id ' \
                    'FROM product_pricelist_version ' \
                    'WHERE '+' and '.join(where) + (where and ' and ' or '')+
                        'pricelist_id = %s ' \
                        'AND active ' \
                        'AND id <> %s', (
                            pricelist_version.pricelist_id.id,
                            pricelist_version.id))
            if cursor.fetchall():
                return False
        return True

    _constraints = [
        (_check_date, 'You cannot have 2 pricelist versions that overlap!',
            ['date_start', 'date_end'])
    ]

    def copy(self, cr, uid, id, default=None, context=None):
        # set active False to prevent overlapping active pricelist
        # versions
        if not default:
            default = {}
        default['active'] = False
        return super(product_pricelist_version, self).copy(cr, uid, id, default, context=context)

class product_pricelist_item(osv.osv):
    def _price_field_get(self, cr, uid, context=None):
        pt = self.pool.get('product.price.type')
        ids = pt.search(cr, uid, [], context=context)
        result = []
        for line in pt.browse(cr, uid, ids, context=context):
            result.append((line.id, line.name))

        result.append((-1, _('Other Pricelist')))
        result.append((-2, _('Supplier Prices on the product form')))
        return result

# Added default function to fetch the Price type Based on Pricelist type.
    def _get_default_base(self, cr, uid, fields, context=None):
        product_price_type_obj = self.pool.get('product.price.type')
        if fields.get('type') == 'purchase':
            product_price_type_ids = product_price_type_obj.search(cr, uid, [('field', '=', 'standard_price')], context=context)
        elif fields.get('type') == 'sale':
            product_price_type_ids = product_price_type_obj.search(cr, uid, [('field','=','list_price')], context=context)
        else:
            return -1
        if not product_price_type_ids:
            return False
        else:
            pricetype = product_price_type_obj.browse(cr, uid, product_price_type_ids, context=context)[0]
            return pricetype.id

    _name = "product.pricelist.item"
    _description = "Pricelist item"
    _order = "sequence, min_quantity desc"
    _defaults = {
        'base': _get_default_base,
        'min_quantity': lambda *a: 0,
        'sequence': lambda *a: 5,
        'price_discount': lambda *a: 0,
    }

    def _check_recursion(self, cr, uid, ids, context=None):
        for obj_list in self.browse(cr, uid, ids, context=context):
            if obj_list.base == -1:
                main_pricelist = obj_list.price_version_id.pricelist_id.id
                other_pricelist = obj_list.base_pricelist_id.id
                if main_pricelist == other_pricelist:
                    return False
        return True

    def _check_margin(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.price_max_margin and item.price_min_margin and (item.price_min_margin > item.price_max_margin):
                return False
        return True

    def _get_product_pricelist(self, cr, uid, ids, context=None):
        result = set()
        for pricelist in self.pool['product.pricelist'].browse(cr, uid, ids, context=context):
            for version_id in pricelist.version_id:
                for item_id in version_id.items_id:
                    result.add(item_id.id)
        return list(result)

    def _get_product_pricelist_version(self, cr, uid, ids, context=None):
        result = set()
        for version in self.pool['product.pricelist.version'].browse(cr, uid, ids, context=context):
            for item_id in version.items_id:
                result.add(item_id.id)
        return list(result)

    _columns = {
        'name': fields.char('Rule Name', help="Explicit rule name for this pricelist line."),
        'price_version_id': fields.many2one('product.pricelist.version', 'Price List Version', required=True, select=True, ondelete='cascade'),
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', ondelete='cascade', help="Specify a template if this rule only applies to one product template. Keep empty otherwise."),
        'product_id': fields.many2one('product.product', 'Product', ondelete='cascade', help="Specify a product if this rule only applies to one product. Keep empty otherwise."),
        'categ_id': fields.many2one('product.category', 'Product Category', ondelete='cascade', help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise."),
        'min_quantity': fields.integer('Min. Quantity', required=True,
            help="For the rule to apply, bought/sold quantity must be greater "
              "than or equal to the minimum quantity specified in this field.\n"
              "Expressed in the default UoM of the product."
            ),
        'sequence': fields.integer('Sequence', required=True, help="Gives the order in which the pricelist items will be checked. The evaluation gives highest priority to lowest sequence and stops as soon as a matching item is found."),
        'base': fields.selection(_price_field_get, 'Based on', required=True, size=-1, help="Base price for computation."),
        'base_pricelist_id': fields.many2one('product.pricelist', 'Other Pricelist'),

        'price_surcharge': fields.float('Price Surcharge',
            digits_compute= dp.get_precision('Product Price'), help='Specify the fixed amount to add or substract(if negative) to the amount calculated with the discount.'),
        'price_discount': fields.float('Price Discount', digits=(16,4)),
        'price_round': fields.float('Price Rounding',
            digits_compute= dp.get_precision('Product Price'),
            help="Sets the price so that it is a multiple of this value.\n" \
              "Rounding is applied after the discount and before the surcharge.\n" \
              "To have prices that end in 9.99, set rounding 10, surcharge -0.01" \
            ),
        'price_min_margin': fields.float('Min. Price Margin',
            digits_compute= dp.get_precision('Product Price'), help='Specify the minimum amount of margin over the base price.'),
        'price_max_margin': fields.float('Max. Price Margin',
            digits_compute= dp.get_precision('Product Price'), help='Specify the maximum amount of margin over the base price.'),
        'company_id': fields.related('price_version_id','company_id',type='many2one',
            readonly=True, relation='res.company', string='Company', store={
                'product.pricelist': (_get_product_pricelist, ['company_id'], 30),
                'product.pricelist.version': (_get_product_pricelist_version, ['pricelist_id'], 30),
                'product.pricelist.item': (lambda self, cr, uid, ids, c=None: ids, ['price_version_id'], 30),
            })
    }

    _constraints = [
        (_check_recursion, 'Error! You cannot assign the Main Pricelist as Other Pricelist in PriceList Item!', ['base_pricelist_id']),
        (_check_margin, 'Error! The minimum margin should be lower than the maximum margin.', ['price_min_margin', 'price_max_margin'])
    ]

    def product_id_change(self, cr, uid, ids, product_id, context=None):
        if not product_id:
            return {}
        prod = self.pool.get('product.product').read(cr, uid, [product_id], ['code','name'])
        if prod[0]['code']:
            return {'value': {'name': prod[0]['code']}}
        return {}



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

