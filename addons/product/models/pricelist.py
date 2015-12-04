# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import chain

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp

#----------------------------------------------------------
# Price lists
#----------------------------------------------------------

class ProductPricelist(models.Model):

    _name = "product.pricelist"
    _description = "Pricelist"
    _order = 'name'

    def _default_get_currency(self):
        company = self.env.user.company_id or self.env['res.company'].search([], limit=1)
        return company.currency_id.id

    name = fields.Char(string='Pricelist Name', required=True, translate=True)
    active = fields.Boolean(help="If unchecked, it will allow you to hide the pricelist without removing it.", default=True)
    item_ids = fields.One2many('product.pricelist.item', 'pricelist_id', string='Pricelist Items', copy=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=_default_get_currency)
    company_id = fields.Many2one('res.company', string='Company')

    @api.multi
    def name_get(self):
        result = []
        for product_pricelist in self:
            name = "%s(%s)" % (product_pricelist.name, product_pricelist.currency_id.name)
            result.append((product_pricelist.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if name and operator == '=' and not args:
            # search on the name of the pricelist and its currency, opposite of name_get(),
            # Used by the magic context filter in the product search view.
            query_args = {'name': name, 'limit': limit, 'lang': self.env.context.get('lang', 'en_US')}
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
            self.env.cr.execute(query, query_args)
            pricelist_ids = [r[0] for r in self.env.cr.fetchall()]
            return self.browse(pricelist_ids).name_get()
        return super(ProductPricelist, self).name_search(name, args, operator=operator, limit=limit)

    @api.multi
    def price_rule_get_multi(self, products_by_qty_by_partner):
        """multi products 'price_get'.
           return: a dict of dict with product_id as key and a dict 'price by pricelist' as value
        """
        pricelists = self
        if not pricelists:
            pricelists = self.search([])
        results = {}
        for pricelist in pricelists:
            subres = pricelist._price_rule_get_multi(products_by_qty_by_partner)
            for product_id, price in subres.items():
                results.setdefault(product_id, {})
                results[product_id][pricelist.id] = price
        return results

    def _price_get_multi(self, products_by_qty_by_partner):
        return dict((key, price[0]) for key, price in self._price_rule_get_multi(products_by_qty_by_partner).items())

    def _price_rule_get_multi(self, products_by_qty_by_partner):
        self.ensure_one()
        date = self.env.context.get('date') and fields.Date.from_string(self.env.context['date']) or fields.Date.today()
        products = map(lambda x: x[0], products_by_qty_by_partner)
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
        self.env.cr.execute(
            'SELECT i.id '
            'FROM product_pricelist_item AS i '
            'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = any(%s))'
            'AND (product_id IS NULL OR product_id = any(%s))'
            'AND (categ_id IS NULL OR categ_id = any(%s)) '
            'AND (pricelist_id = %s) '
            'AND ((i.date_start IS NULL OR i.date_start<=%s) AND (i.date_end IS NULL OR i.date_end>=%s))'
            'ORDER BY applied_on, min_quantity desc',
            (prod_tmpl_ids, prod_ids, categ_ids, self.id, date, date))

        item_ids = [x[0] for x in self.env.cr.fetchall()]
        pricelist_items = self.env['product.pricelist.item'].browse(item_ids)
        results = {}
        for product, qty, partner in products_by_qty_by_partner:
            results[product.id] = 0.0
            suitable_rule = False

            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.
            qty_uom_id = self.env.context.get('uom') or product.uom_id.id
            price_uom_id = product.uom_id.id
            qty_in_product_uom = qty
            if qty_uom_id != product.uom_id.id:
                try:
                    qty_in_product_uom = self.env['product.uom'].browse(self.env.context.get('uom'))._compute_qty(qty, product.uom_id.id)
                except UserError:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass

            # if Public user try to access standard price from website sale, need to call _price_get.
            price = self.env['product.template']._price_get([product], 'list_price')[product.id]
            price_uom_id = qty_uom_id
            for rule in pricelist_items:
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
                    price_tmp = rule.base_pricelist_id._price_get_multi([(product, qty, partner)])[product.id]
                    price = rule.base_pricelist_id.currency_id.compute(price_tmp, self.currency_id, round=False)
                else:
                    # if base option is public price take sale price else cost price of product
                    # price_get returns the price in the context UoM, i.e. qty_uom_id
                    price = self.env['product.template']._price_get([product], rule.base)[product.id]

                convert_to_price_uom = (lambda price: product.uom_id._compute_price(price, price_uom_id))

                if price:
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
                user_company = self.env.user.company_id
                price = user_company.currency_id.compute(price, self.currency_id)
            results[product.id] = (price, suitable_rule and suitable_rule.id)
        return results

    @api.multi
    def price_get(self, product_id, qty, partner=None):
        self.ensure_one()
        return dict((key, price[0]) for key, price in self.price_rule_get(product_id, qty, partner=partner).items())

    @api.multi
    def price_rule_get(self, product_id, qty, partner=None):
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)
        res_multi = self.price_rule_get_multi(products_by_qty_by_partner=[(product, qty, partner)])
        return res_multi[product_id]


class ProductPricelistItem(models.Model):
    _name = "product.pricelist.item"
    _description = "Pricelist item"
    _order = "applied_on, min_quantity desc"

    product_tmpl_id = fields.Many2one('product.template', string='Product Template', ondelete='cascade', help="Specify a template if this rule only applies to one product template. Keep empty otherwise.")
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade', help="Specify a product if this rule only applies to one product. Keep empty otherwise.")
    categ_id = fields.Many2one('product.category', string='Product Category', ondelete='cascade', help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")
    min_quantity = fields.Integer('Min. Quantity', help="For the rule to apply, bought/sold quantity must be greater "
          "than or equal to the minimum quantity specified in this field.\n"
          "Expressed in the default unit of measure of the product.", default=1)
    applied_on = fields.Selection([('3_global', 'Global'), ('2_product_category', ' Product Category'), ('1_product', 'Product'), ('0_product_variant', 'Product Variant')], string="Apply On", required=True,
        help='Pricelist Item applicable on selected option', default='3_global')
    sequence = fields.Integer(required=True, help="Gives the order in which the pricelist items will be checked. The evaluation gives highest priority to lowest sequence and stops as soon as a matching item is found.", default=5)
    base = fields.Selection([('list_price', 'Public Price'), ('standard_price', 'Cost'), ('pricelist', 'Other Pricelist')], string="Based on", required=True,
        help='Base price for computation. \n Public Price: The base price will be the Sale/public Price. \n Cost Price : The base price will be the cost price. \n Other Pricelist : Computation of the base price based on another Pricelist.', default='list_price')
    base_pricelist_id = fields.Many2one('product.pricelist', string='Other Pricelist')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    price_surcharge = fields.Float(string='Price Surcharge', digits=dp.get_precision('Product Price'),
        help='Specify the fixed amount to add or substract(if negative) to the amount calculated with the discount.')
    price_discount = fields.Float(string='Price Discount', digits=(16, 2), default=0.0)
    price_round = fields.Float(string='Price Rounding', digits=dp.get_precision('Product Price'),
        help="Sets the price so that it is a multiple of this value.\n" \
            "Rounding is applied after the discount and before the surcharge.\n" \
            "To have prices that end in 9.99, set rounding 10, surcharge -0.01")
    price_min_margin = fields.Float(string='Min. Price Margin', digits=dp.get_precision('Product Price'),
        help='Specify the minimum amount of margin over the base price.')
    price_max_margin = fields.Float(string='Max. Price Margin', digits=dp.get_precision('Product Price'),
        help='Specify the maximum amount of margin over the base price.')
    company_id = fields.Many2one('res.company', related='pricelist_id.company_id', readonly=True, string='Company', store=True)
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', readonly=True, string='Currency', store=True)
    date_start = fields.Date(string='Start Date', help="Starting date for the pricelist item validation")
    date_end = fields.Date(string='End Date', help="Ending valid for the pricelist item validation")
    compute_price = fields.Selection([('fixed', 'Fix Price'), ('percentage', 'Percentage (discount)'), ('formula', 'Formula')], index=True, default='fixed')
    fixed_price = fields.Float(string='Fixed Price')
    percent_price = fields.Float(string='Percentage Price')

    @api.constrains('price_min_margin', 'price_max_margin')
    def _check_margin(self):
        for item in self:
            if item.price_min_margin > item.price_max_margin:
                raise ValidationError(_("Error! The minimum margin should be lower than the maximum margin."))

    @api.constrains('base_pricelist_id')
    def _check_recursion(self):
        for item in self:
            if item.base == 'pricelist' and item.pricelist_id == item.base_pricelist_id:
                raise ValidationError(_("Error! You cannot assign the Main Pricelist as Other Pricelist in PriceList Item!"))

class ProductPricelistItemNew(models.Model):
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

    def _compute_pricelist_item_name_price(self):
        for item in self:
            if item.categ_id:
                item.name = _("Category: %s") % (item.categ_id.name)
            elif item.product_tmpl_id:
                item.name = item.product_tmpl_id.name
            elif item.product_id:
                item.name = item.product_id.display_name.replace('[%s]' % item.product_id.code, '')
            else:
                item.name = _("All Products")

            if item.compute_price == 'fixed':
                item.price = ("%s %s") % (item.fixed_price, item.pricelist_id.currency_id.name)
            elif item.compute_price == 'percentage':
                item.price = _("%s %% discount") % (item.percent_price)
            else:
                item.price = _("%s %% discount and %s surcharge") % (abs(item.price_discount), item.price_surcharge)

       #functional fields used for usability purposes
    name = fields.Char(compute='_compute_pricelist_item_name_price', help="Explicit rule name for this pricelist line.")
    price = fields.Char(compute='_compute_pricelist_item_name_price',  help="Explicit rule name for this pricelist line.")

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
