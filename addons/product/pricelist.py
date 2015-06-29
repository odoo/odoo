# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import chain
import time

from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import fields, osv
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError

#----------------------------------------------------------
# Price lists
#----------------------------------------------------------

class product_pricelist(osv.osv):

    _name = "product.pricelist"
    _description = "Pricelist"
    _order = 'name'
    _columns = {
        'name': fields.char('Pricelist Name', required=True, translate=True),
        'active': fields.boolean('Active', help="If unchecked, it will allow you to hide the pricelist without removing it."),
        'item_ids': fields.one2many('product.pricelist.item', 'pricelist_id', 'Pricelist Items', copy=True),
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
            for product_id, price in subres.items():
                results.setdefault(product_id, {})
                results[product_id][pricelist.id] = price
        return results

    def _price_get_multi(self, cr, uid, pricelist, products_by_qty_by_partner, context=None):
        return dict((key, price[0]) for key, price in self._price_rule_get_multi(cr, uid, pricelist, products_by_qty_by_partner, context=context).items())

    def _price_rule_get_multi(self, cr, uid, pricelist, products_by_qty_by_partner, context=None):
        context = context or {}
        date = 'date' in context and context['date'][0:10] or time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        products = map(lambda x: x[0], products_by_qty_by_partner)
        product_uom_obj = self.pool.get('product.uom')

        if not products:
            return {}

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
            'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = any(%s))'
            'AND (product_id IS NULL OR product_id = any(%s))'
            'AND (categ_id IS NULL OR categ_id = any(%s)) '
            'AND (pricelist_id = %s) '
            'AND ((i.date_start IS NULL OR i.date_start<=%s) AND (i.date_end IS NULL OR i.date_end>=%s))'
            'ORDER BY applied_on, min_quantity desc',
            (prod_tmpl_ids, prod_ids, categ_ids, pricelist.id, date, date))

        item_ids = [x[0] for x in cr.fetchall()]
        items = self.pool.get('product.pricelist.item').browse(cr, uid, item_ids, context=context)
        results = {}
        for product, qty, partner in products_by_qty_by_partner:
            results[product.id] = 0.0
            rule_id = False

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
                except UserError:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass

            # if Public user try to access standard price from website sale, need to call _price_get.
            price = product.list_price or 0.0
            price_uom_id = qty_uom_id
            for rule in items:
                if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
                    continue
                if is_product_template:
                    if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and \
                            (product.product_variant_count > 1 or product.product_variant_ids[0].id != rule.product_id.id):
                        # product rule acceptable on template if has only one variant
                        continue
                else:
                    if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and product.id != rule.product_id.id:
                        continue

                if rule.base == 'pricelist' and rule.base_pricelist_id:
                    price = self._price_get_multi(cr, uid, rule.base_pricelist_id, [(product, qty, partner)], context=context)[product.id]
                else:
                    # if base option is public price take sale price else cost price of product
                    price = product.list_price or 0.0 if rule.base == 'list_price' else product.standard_price or 0.0
                if price is not False:
                    if rule.compute_price == 'fixed':
                        price = rule.fixed_price
                    elif rule.compute_price == 'percentage':
                        price = (price - (price * (rule.percent_price/100))) or 0.0
                    else:
                        price_limit = price
                        price = (price - (price * (rule.price_discount/100))) or 0.0
                        if rule.price_round:
                            price = tools.float_round(price, precision_rounding=rule.price_round)
                        if rule.price_surcharge:
                            price += rule.price_surcharge
                        if rule.price_min_margin:
                            price = max(price, price_limit + rule.price_min_margin)
                        if rule.price_max_margin:
                            price = min(price, price_limit + rule.price_max_margin)
                    rule_id = rule.id
                break
            # Final price conversion into pricelist currency curreny and UoM
            user_company = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id
            currency_price = self.pool['res.currency'].compute(cr, uid, user_company.currency_id.id, pricelist.currency_id.id, price, context=context)
            price = product_uom_obj._compute_price(cr, uid, product.uom_id.id, currency_price, price_uom_id)
            results[product.id] = (price, rule_id)
        return results

    def price_get(self, cr, uid, ids, prod_id, qty, partner=None, context=None):
        return dict((key, price[0]) for key, price in self.price_rule_get(cr, uid, ids, prod_id, qty, partner=partner, context=context).items())

    def price_rule_get(self, cr, uid, ids, prod_id, qty, partner=None, context=None):
        product = self.pool.get('product.product').browse(cr, uid, prod_id, context=context)
        res_multi = self.price_rule_get_multi(cr, uid, ids, products_by_qty_by_partner=[(product, qty, partner)], context=context)
        res = res_multi[prod_id]
        return res

class product_pricelist_item(osv.osv):

    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        res = super(product_pricelist_item, self).default_get(cr, uid, fields, context=context)
        pricelist_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'product.list0')
        if 'pricelist_id' in fields:
            res.update({'pricelist_id': pricelist_id or False})
        if context.get('default_product_id'):
            product = self.pool['product.product'].browse(cr, uid, context.get('default_product_id'), context=context)
            res.update({'fixed_price': product.lst_price if product else 0.0})
        if context.get('default_product_tmpl_id'):
            template = self.pool['product.template'].browse(cr, uid, context.get('default_product_tmpl_id'), context=context)
            res.update({'fixed_price': template.list_price if template else 0.0})
        return res

    def onchange_apply(self, cr, uid, ids, applied_on, context=None):
        data = {'1': {'product_id': False, 'categ_id': False},
                '2': {'product_tmpl_id': False, 'product_id': False},
                '3': {'categ_id': False, 'product_tmpl_id': False, 'product_id': False},
                '0': {'product_tmpl_id': False, 'categ_id': False}}
        return {'value': data[applied_on]}

    _name = "product.pricelist.item"
    _description = "Pricelist item"
    _order = "applied_on, min_quantity desc"
    _defaults = {
        'base': 'list_price',
        'min_quantity': lambda *a: 1,
        'sequence': lambda *a: 5,
        'price_discount': lambda *a: 0,
        'applied_on': '3',
    }

    def _check_recursion(self, cr, uid, ids, context=None):
        for obj_list in self.browse(cr, uid, ids, context=context):
            if obj_list.base == 'pricelist':
                main_pricelist = obj_list.pricelist_id.id
                other_pricelist = obj_list.base_pricelist_id.id
                if main_pricelist == other_pricelist:
                    return False
        return True

    def _check_margin(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.price_max_margin and item.price_min_margin and (item.price_min_margin > item.price_max_margin):
                return False
        return True

    def _price_list_item_name(self, cr, uid, ids, fields, args, context=None):
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            res[item.id] = {'name': '', 'price': ''}
            if item.categ_id:
                res[item.id]['name'] = _("Category: %s") % (item.categ_id.name)
            elif item.product_tmpl_id:
                res[item.id]['name'] = item.product_tmpl_id.name
            elif item.product_id:
                res[item.id]['name'] = item.product_id.display_name.replace('[%s]' % item.product_id.code, '')
            else:
                res[item.id]['name'] = _("All Products")
            if item.compute_price == 'fixed':
                res[item.id]['price'] = ("%s %s") % (item.fixed_price, item.pricelist_id.currency_id.name)
            elif item.compute_price == 'percentage':
                res[item.id]['price'] = _("%s %% discount") % (item.percent_price)
            else:
                res[item.id]['price'] = _("%s %% discount and %s surcharge") % (abs(item.price_discount), item.price_surcharge)
        return res

    _columns = {
        'name': fields.function(_price_list_item_name, type="char", string='Name', multi='price_item', help="Explicit rule name for this pricelist line."),
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', ondelete='cascade', help="Specify a template if this rule only applies to one product template. Keep empty otherwise."),
        'product_id': fields.many2one('product.product', 'Product', ondelete='cascade', help="Specify a product if this rule only applies to one product. Keep empty otherwise."),
        'categ_id': fields.many2one('product.category', 'Product Category', ondelete='cascade', help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise."),
        'min_quantity': fields.integer('Min. Quantity',
            help="For the rule to apply, bought/sold quantity must be greater "
              "than or equal to the minimum quantity specified in this field.\n"
              "Expressed in the default unit of measure of the product."
            ),
        'applied_on': fields.selection([('3', 'Global'),('2', ' Product Category'), ('1', 'Product'), ('0', 'Product Variant')], string="Apply On", required=True,
            help='Pricelist Item applicable on selected option'),
        'sequence': fields.integer('Sequence', required=True, help="Gives the order in which the pricelist items will be checked. The evaluation gives highest priority to lowest sequence and stops as soon as a matching item is found."),
        'base': fields.selection([('list_price', 'Public Price'), ('standard_price', 'Cost'), ('pricelist', 'Other Pricelist')], string="Based on", required=True,
            help='Base price for computation. \n Public Price: The base price will be the Sale/public Price. \n Cost Price : The base price will be the cost price. \n Other Pricelist : Computation of the base price based on another Pricelist.'),
        'base_pricelist_id': fields.many2one('product.pricelist', 'Other Pricelist'),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
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
        'company_id': fields.related('pricelist_id','company_id',type='many2one',
            readonly=True, relation='res.company', string='Company', store=True),
        'currency_id': fields.related('pricelist_id', 'currency_id', type='many2one',
            readonly=True, relation='res.currency', string='Currency', store=True),
        'date_start': fields.date('Start Date', help="Starting date for the pricelist item validation"),
        'date_end': fields.date('End Date', help="Ending valid for the pricelist item validation"),
        'compute_price': fields.selection([('fixed', 'Fix Price'), ('percentage', 'Percentage (discount)'), ('formula', 'Formula')], select=True, default='fixed'),
        'fixed_price': fields.float('Fixed Price'),
        'percent_price': fields.float('Percentage Price'),
        'price': fields.function(_price_list_item_name, type="char", string='Price', multi='price_item', help="Explicit rule name for this pricelist line."),
    }

    _constraints = [
        (_check_recursion, 'Error! You cannot assign the Main Pricelist as Other Pricelist in PriceList Item!', ['base_pricelist_id']),
        (_check_margin, 'Error! The minimum margin should be lower than the maximum margin.', ['price_min_margin', 'price_max_margin'])
    ]
    _sql_constraints = [
        ('name_uniq', 'unique(categ_id, product_id, product_tmpl_id, min_quantity, date_end, date_start)', 'Pricelist items must be unique!'),
    ]
