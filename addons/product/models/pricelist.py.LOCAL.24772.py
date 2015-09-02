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
from openerp import api, models, fields as Fields

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
        date = context.get('date') and context['date'][0:10] or time.strftime(DEFAULT_SERVER_DATE_FORMAT)
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
            suitable_rule = False

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
                        cr, uid, context['uom'], qty, product.uom_id.id)
                except UserError:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass

            # if Public user try to access standard price from website sale, need to call _price_get.
            price = self.pool['product.template']._price_get(cr, uid, [product], 'list_price', context=context)[product.id]

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

                if rule.categ_id:
                    cat = product.categ_id
                    while cat:
                        if cat.id == rule.categ_id.id:
                            break
                        cat = cat.parent_id
                    if not cat:
                        continue

                if rule.base == 'pricelist' and rule.base_pricelist_id:
                    price_tmp = self._price_get_multi(cr, uid, rule.base_pricelist_id, [(product, qty, partner)], context=context)[product.id]
                    ptype_src = rule.base_pricelist_id.currency_id.id
                    price = self.pool['res.currency'].compute(cr, uid, ptype_src, pricelist.currency_id.id, price_tmp, round=False, context=context)
                else:
                    # if base option is public price take sale price else cost price of product
                    # price_get returns the price in the context UoM, i.e. qty_uom_id
                    price = self.pool['product.template']._price_get(cr, uid, [product], rule.base, context=context)[product.id]

                convert_to_price_uom = (lambda price: product_uom_obj._compute_price(
                                            cr, uid, product.uom_id.id,
                                            price, price_uom_id))

                if price is not False:
                    if rule.compute_price == 'fixed':
                        price = convert_to_price_uom(rule.fixed_price)
                    elif rule.compute_price == 'percentage':
                        price = (price - (price * (rule.percent_price / 100))) or 0.0
                    else:
                        #complete formula
                        price_limit = price
                        price = (price - (price * (rule.price_discount / 100))) or 0.0
                        if rule.price_round:
                            price = tools.float_round(price, precision_rounding=rule.price_round)

                        if rule.price_surcharge:
                            price_surcharge = convert_to_price_uom(rule.price_surcharge)
                            price += price_surcharge

                        if rule.price_min_margin:
                            price_min_margin = convert_to_price_uom(rule.price_min_margin)
                            price = max(price, price_limit + price_min_margin)

                        if rule.price_max_margin:
                            price_max_margin = convert_to_price_uom(rule.price_max_margin)
                            price = min(price, price_limit + price_max_margin)
                    suitable_rule = rule
                break
            # Final price conversion into pricelist currency
            if suitable_rule and suitable_rule.compute_price != 'fixed' and suitable_rule.base != 'pricelist':
                user_company = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id
                price = self.pool['res.currency'].compute(cr, uid, user_company.currency_id.id, pricelist.currency_id.id, price, context=context)

            results[product.id] = (price, suitable_rule and suitable_rule.id or False)
        return results

    def price_get(self, cr, uid, ids, prod_id, qty, partner=None, context=None):
        return dict((key, price[0]) for key, price in self.price_rule_get(cr, uid, ids, prod_id, qty, partner=partner, context=context).items())

    def price_rule_get(self, cr, uid, ids, prod_id, qty, partner=None, context=None):
        product = self.pool.get('product.product').browse(cr, uid, prod_id, context=context)
        res_multi = self.price_rule_get_multi(cr, uid, ids, products_by_qty_by_partner=[(product, qty, partner)], context=context)
        res = res_multi[prod_id]
        return res

class product_pricelist_item(osv.osv):
    _name = "product.pricelist.item"
    _description = "Pricelist item"
    _order = "applied_on, min_quantity desc"

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

    _columns = {
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', ondelete='cascade', help="Specify a template if this rule only applies to one product template. Keep empty otherwise."),
        'product_id': fields.many2one('product.product', 'Product', ondelete='cascade', help="Specify a product if this rule only applies to one product. Keep empty otherwise."),
        'categ_id': fields.many2one('product.category', 'Product Category', ondelete='cascade', help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise."),
        'min_quantity': fields.integer('Min. Quantity',
            help="For the rule to apply, bought/sold quantity must be greater "
              "than or equal to the minimum quantity specified in this field.\n"
              "Expressed in the default unit of measure of the product."
            ),
        'applied_on': fields.selection([('3_global', 'Global'),('2_product_category', ' Product Category'), ('1_product', 'Product'), ('0_product_variant', 'Product Variant')], string="Apply On", required=True,
            help='Pricelist Item applicable on selected option'),
        'sequence': fields.integer('Sequence', required=True, help="Gives the order in which the pricelist items will be checked. The evaluation gives highest priority to lowest sequence and stops as soon as a matching item is found."),
        'base': fields.selection([('list_price', 'Public Price'), ('standard_price', 'Cost'), ('pricelist', 'Other Pricelist')], string="Based on", required=True,
            help='Base price for computation. \n Public Price: The base price will be the Sale/public Price. \n Cost Price : The base price will be the cost price. \n Other Pricelist : Computation of the base price based on another Pricelist.'),
        'base_pricelist_id': fields.many2one('product.pricelist', 'Other Pricelist'),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
        'price_surcharge': fields.float('Price Surcharge',
            digits_compute= dp.get_precision('Product Price'), help='Specify the fixed amount to add or substract(if negative) to the amount calculated with the discount.'),
        'price_discount': fields.float('Price Discount', digits=(16,2)),
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
    }

    _defaults = {
        'base': 'list_price',
        'min_quantity': 1,
        'sequence': 5,
        'price_discount': 0,
        'applied_on': '3_global',
    }
    _constraints = [
        (_check_recursion, 'Error! You cannot assign the Main Pricelist as Other Pricelist in PriceList Item!', ['base_pricelist_id']),
        (_check_margin, 'Error! The minimum margin should be lower than the maximum margin.', ['price_min_margin', 'price_max_margin'])
    ]


class product_pricelist_item_new(models.Model):
    _inherit = "product.pricelist.item"

    _applied_on_field_map = {
        '0_product_variant': 'product_id',
        '1_product': 'product_tmpl_id',
        '2_product_category': 'categ_id',
    }

    _compute_price_field_map = {
        'fixed': ['fixed_price'],
        'percentage': ['percent_price'],
        'formula': ['price_discount', 'price_surcharge', 'price_round', 'price_min_margin', 'price_max_margin'],
    }

    @api.one
    @api.depends('categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        if self.categ_id:
            self.name = _("Category: %s") % (self.categ_id.name)
        elif self.product_tmpl_id:
            self.name = self.product_tmpl_id.name
        elif self.product_id:
            self.name = self.product_id.display_name.replace('[%s]' % self.product_id.code, '')
        else:
            self.name = _("All Products")

        if self.compute_price == 'fixed':
            self.price = ("%s %s") % (self.fixed_price, self.pricelist_id.currency_id.name)
        elif self.compute_price == 'percentage':
            self.price = _("%s %% discount") % (self.percent_price)
        else:
            self.price = _("%s %% discount and %s surcharge") % (abs(self.price_discount), self.price_surcharge)

    #functional fields used for usability purposes
    name = Fields.Char(compute='_get_pricelist_item_name_price', string='Name', multi='item_name_price', help="Explicit rule name for this pricelist line.")
    price = Fields.Char(compute='_get_pricelist_item_name_price', string='Price', multi='item_name_price', help="Explicit rule name for this pricelist line.")

    @api.onchange('applied_on')
    def _onchange_applied_on(self):
        for applied_on, field in self._applied_on_field_map.iteritems():
            if self.applied_on != applied_on:
                setattr(self, field, False)

    @api.onchange('compute_price')
    def _onchange_compute_price(self):
        for compute_price, field in self._compute_price_field_map.iteritems():
            if self.compute_price != compute_price:
                for f in field:
                    setattr(self, f, 0.0)
