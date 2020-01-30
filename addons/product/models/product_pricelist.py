# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr
from odoo.tools.misc import get_lang


class Pricelist(models.Model):
    _name = "product.pricelist"
    _description = "Pricelist"
    _order = "sequence asc, id desc"

    def _get_default_currency_id(self):
        return self.env.company.currency_id.id

    name = fields.Char('Pricelist Name', required=True, translate=True)
    active = fields.Boolean('Active', default=True, help="If unchecked, it will allow you to hide the pricelist without removing it.")
    item_ids = fields.One2many(
        'product.pricelist.item', 'pricelist_id', 'Pricelist Items',
        copy=True)
    currency_id = fields.Many2one('res.currency', 'Currency', default=_get_default_currency_id, required=True)
    company_id = fields.Many2one('res.company', 'Company')

    sequence = fields.Integer(default=16)
    country_group_ids = fields.Many2many('res.country.group', 'res_country_group_pricelist_rel',
                                         'pricelist_id', 'res_country_group_id', string='Country Groups')

    discount_policy = fields.Selection([
        ('with_discount', 'Discount included in the price'),
        ('without_discount', 'Show public price & discount to the customer')],
        default='with_discount', required=True)

    def name_get(self):
        return [(pricelist.id, '%s (%s)' % (pricelist.name, pricelist.currency_id.name)) for pricelist in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if name and operator == '=' and not args:
            # search on the name of the pricelist and its currency, opposite of name_get(),
            # Used by the magic context filter in the product search view.
            query_args = {'name': name, 'limit': limit, 'lang': get_lang(self.env).code}
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
            self._cr.execute(query, query_args)
            ids = [r[0] for r in self._cr.fetchall()]
            # regular search() to apply ACLs - may limit results below limit in some cases
            pricelist_ids = self._search([('id', 'in', ids)], limit=limit, access_rights_uid=name_get_uid)
            if pricelist_ids:
                return models.lazy_name_get(self.browse(pricelist_ids).with_user(name_get_uid))
        return super(Pricelist, self)._name_search(name, args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    def _compute_price_rule_multi(self, products, quantity, uom, currency=None, date=False):
        """ Low-level method - Multi pricelist, multi products
        Returns: dict{product_id: dict{pricelist_id: (price, suitable_rule)} }"""
        if not self.ids:
            pricelists = self.search([])
        else:
            pricelists = self
        results = {}
        for pricelist in pricelists:
            subres = pricelist._compute_price_rule(products, quantity, uom, currency, date=date)
            for product_id, price in subres.items():
                results.setdefault(product_id, {})
                results[product_id][pricelist.id] = price
        return results

    def _compute_price_rule_get_items(self, date, prod_tmpl_ids, prod_ids, categ_ids):
        self.ensure_one()
        # Load all rules
        self.env['product.pricelist.item'].flush(['price', 'currency_id', 'company_id'])
        self.env.cr.execute(
            """
            SELECT
                item.id
            FROM
                product_pricelist_item AS item
            LEFT JOIN product_category AS categ ON item.categ_id = categ.id
            WHERE
                (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))
                AND (item.product_id IS NULL OR item.product_id = any(%s))
                AND (item.categ_id IS NULL OR item.categ_id = any(%s))
                AND (item.pricelist_id = %s)
                AND (item.date_start IS NULL OR item.date_start<=%s)
                AND (item.date_end IS NULL OR item.date_end>=%s)
            ORDER BY
                item.applied_on, item.min_quantity desc, categ.complete_name desc, item.id desc
            """,
            (prod_tmpl_ids, prod_ids, categ_ids, self.id, date, date))
        # NOTE: if you change `order by` on that query, make sure it matches
        # _order from model to avoid inconstencies and undeterministic issues.

        item_ids = [x[0] for x in self.env.cr.fetchall()]
        return self.env['product.pricelist.item'].browse(item_ids)

    def _compute_price_rule(self, products, quantity, uom, currency=None, date=False):
        """ Low-level method - Mono pricelist, multi products
        Returns: dict{product_id: (price, suitable_rule) for the given pricelist}

            :param product: products
            :type product: product.product or product.template
            :param float quantity:
            :param uom.uom uom: intermediate unit of measure
            :param date: validity date
            :type date: date or datetime
        """
        if not products:
            return {}

        if not self:
            # Default price, even if no pricelist defined
            # = Sales price or contextual price
            prices = products.price_compute(
                'list_price',
                uom=uom,
                date=date,
                currency=currency)
            return {id: (prices[id], []) for id in products.ids}

        # Ensure subsequent calls are all done in pricelist company if defined.
        self = self.with_company(self.company_id)
        company = self.company_id or self.env.company

        if not date:
            date = fields.Date.context_today(self)
        else:
            date = fields.Date.to_date(date)  # boundary conditions differ if we have a datetime

        categ_ids = {}
        for p in products:
            categ = p.categ_id
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
        categ_ids = list(categ_ids)

        is_product_template = not products[0].is_product_variant
        if is_product_template:
            prod_tmpl_ids = products.ids
            # all variants of all products
            prod_ids = products.product_variant_ids.ids
        else:
            prod_ids = products.ids
            prod_tmpl_ids = products.product_tmpl_id.ids

        items = self._compute_price_rule_get_items(date, prod_tmpl_ids, prod_ids, categ_ids)
        # VFE TODO prefetch sales and cost prices for all products ? compare perfs

        results = {}
        for product in products:
            results[product.id] = 0.0
            suitable_rule = self.env['product.pricelist.item']
            child_rules = []

            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.
            product_uom = product.uom_id
            target_uom = uom or product_uom
            qty_in_product_uom = target_uom._compute_quantity(quantity, product.uom_id, round=False)
            # if Public user try to access standard price from website sale, need to call price_compute.

            for rule in items:
                """ Check if pricelist rule is applicable to given product/template """
                if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
                    continue
                if is_product_template:
                    if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and not (product.product_variant_count == 1 and product.product_variant_id.id == rule.product_id.id):
                        # product rule acceptable on template if it has only one variant
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

                """ Compute base price of pricelist rule """
                price, child_rules = rule._get_base_price(
                    product,
                    qty_in_product_uom,
                    product_uom,
                    date,
                    self.currency_id,
                )

                """ Apply formula. """
                if rule.compute_price == 'percentage':
                    price = (price - (price * (rule.percent_price / 100))) or 0.0
                elif rule.compute_price == 'formula':
                    # complete formula
                    price_limit = price
                    price = (price - (price * (rule.price_discount / 100))) or 0.0
                    if rule.price_round:
                        price = tools.float_round(price, precision_rounding=rule.price_round)

                    if rule.price_surcharge:
                        price += rule.price_surcharge

                    if rule.price_min_margin:
                        price = max(price, price_limit + rule.price_min_margin)

                    if rule.price_max_margin:
                        price = min(price, price_limit + rule.price_max_margin)
                suitable_rule = rule
                # Break at first applicable rule found (considering rule ordering)
                break

            if suitable_rule:
                # VFE TODO move price computation here, based on suitable_rule
                rules = [suitable_rule.id] + child_rules
            else:
                price = product.price_compute('list_price', uom=product_uom, date=date, currency=self.currency_id)[product.id]
                rules = []

            # The price has to be returned in the target uom.
            if product_uom != target_uom:
                price = product_uom._compute_price(price, target_uom)

            if currency and currency != self.currency_id:
                price = self.currency_id._convert(
                    from_amount=price,
                    to_currency=currency,
                    company=company,
                    date=date,
                    round=False
                )

            results[product.id] = (price, rules)

        return results

    # New methods: product based
    def get_products_price(self, products, quantity, uom, currency=None, date=False):
        """ For a given pricelist, return price for products
        Returns: dict{product_id: product price}, in the given pricelist """
        return {
            product_id: res_tuple[0]
            for product_id, res_tuple in self._compute_price_rule(
                products,
                quantity,
                uom,
                currency,
                date=date,
            ).items()
        }

    def get_product_price(self, product, quantity, uom, currency=None, date=False):
        """ For a given pricelist, return price for a given product """
        product.ensure_one()
        return self._compute_price_rule(
            product,
            quantity,
            uom,
            currency,
            date=date,
        ).get(product.id)[0]

    def _get_product_price_rules(self, product, quantity, uom, currency=None, date=False):
        """ For a given pricelist, return price and list of rules for a given product """
        product.ensure_one()
        return self._compute_price_rule(
            product,
            quantity,
            uom,
            currency,
            date=date,
        ).get(product.id)

    def _get_detailed_prices(self, **pricelist_kwargs):
        """Return the price with and without discounts.

        Depends on the discount_policy of the current pricelist and on
        the chain of pricelist dependencies.

        The price without discount may be the sales_price, the cost price,
        a fixed price, or even the price given by another pricelist
        (formula or not).

        :returns: price, price_without_discount
        :rtype: tuple(float, float)
        """
        price = price_without_discount = 0.0
        if not self or self.discount_policy == 'with_discount':
            # if not pricelist: use product lst_price instead...
            price = self.get_product_price(**pricelist_kwargs)
            price_without_discount = price
        else:
            # Price in pricelist currency (== order.currency_id)
            price, rule_ids = self._get_product_price_rules(**pricelist_kwargs)
            price_without_discount = price

            if rule_ids:
                last_rule = self.env['product.pricelist.item']
                price_without_discount = 0
                for rule_id in rule_ids:
                    rule = self.env['product.pricelist.item'].browse(rule_id)
                    if rule.pricelist_id.discount_policy == 'without_discount':
                        last_rule = rule
                    else:
                        # The price given by rule is the price before discount
                        # because its pricelist has with_discount as discount_policy.
                        break

                if last_rule:
                    price_without_discount = last_rule._get_base_price(
                        **pricelist_kwargs)[0]
                    # 0 = price, 1 = sub_rules
                else:
                    price_without_discount = price

        return price, price_without_discount

    def _get_detailed_prices(self, **pricelist_kwargs):
        """Return the price with and without discounts.

        Depends on the discount_policy of the current pricelist and on
        the chain of pricelist dependencies.

        The price without discount may be the sales_price, the cost price,
        a fixed price, or even the price given by another pricelist
        (formula or not).

        :returns: price, price_without_discount
        :rtype: tuple(float, float)
        """
        price = price_without_discount = 0.0
        if not self or self.discount_policy == 'with_discount':
            # if not pricelist: use product lst_price instead...
            price = self.get_product_price(**pricelist_kwargs)
            price_without_discount = price
        else:
            # Price in pricelist currency (== order.currency_id)
            price, rule_ids = self._get_product_price_rules(**pricelist_kwargs)
            price_without_discount = price

            if rule_ids:
                last_rule = self.env['product.pricelist.item']
                price_without_discount = 0
                for rule_id in rule_ids:
                    rule = self.env['product.pricelist.item'].browse(rule_id)
                    if rule.pricelist_id.discount_policy == 'without_discount':
                        last_rule = rule
                    else:
                        # The price given by rule is the price before discount
                        # because its pricelist has with_discount as discount_policy.
                        break

                if last_rule:
                    price_without_discount = last_rule._get_base_price_rules(
                        **pricelist_kwargs)[0]
                    # 0 = price, 1 = sub_rules
                else:
                    price_without_discount = price

        return price, price_without_discount

    def _get_partner_pricelist_multi_search_domain_hook(self):
        return [('active', '=', True)]

    def _get_partner_pricelist_multi_filter_hook(self):
        return self.filtered('active')

    def _get_partner_pricelist_multi(self, partner_ids, company_id=None):
        """ Retrieve the applicable pricelist for given partners in a given company.

            It will return the first found pricelist in this order:
            First, the pricelist of the specific property (res_id set), this one
                   is created when saving a pricelist on the partner form view.
            Else, it will return the pricelist of the partner country group
            Else, it will return the generic property (res_id not set), this one
                  is created on the company creation.
            Else, it will return the first available pricelist

            :param company_id: if passed, used for looking up properties,
                instead of current user's company
            :return: a dict {partner_id: pricelist}
        """
        # `partner_ids` might be ID from inactive partners. We should use active_test
        # as we will do a search() later (real case for website public user).
        Partner = self.env['res.partner'].with_context(active_test=False)

        Property = self.env['ir.property'].with_company(company_id)

        # if no specific property, try to find a fitting pricelist
        result = Property.get_multi('property_product_pricelist', Partner._name, partner_ids)

        remaining_partner_ids = [
            partner_id for partner_id, pl in result.items()
            if not pl or not pl._get_partner_pricelist_multi_filter_hook()
        ]
        if remaining_partner_ids:
            Pricelist = self.env['product.pricelist']
            pl_domain = self._get_partner_pricelist_multi_search_domain_hook()
            # get fallback pricelist when no pricelist for a given country
            pl_fallback = (
                Pricelist.search(pl_domain + [('country_group_ids', '=', False)], limit=1) or
                Property.get('property_product_pricelist', 'res.partner').filtered('active') or
                Pricelist.search(pl_domain, limit=1)
            )
            # group partners by country, and find a pricelist for each country
            domain = [('id', 'in', remaining_partner_ids)]
            groups = Partner.read_group(domain, ['country_id'], ['country_id'])
            for group in groups:
                country_id = group['country_id'] and group['country_id'][0]
                pl = Pricelist.search(pl_domain + [('country_group_ids.country_ids', '=', country_id)], limit=1)
                pl = pl or pl_fallback
                for pid in Partner.search(group['__domain']).ids:
                    result[pid] = pl

        return result

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Pricelists'),
            'template': '/product/static/xls/product_pricelist.xls'
        }]


class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    pricelist_ids = fields.Many2many('product.pricelist', 'res_country_group_pricelist_rel',
                                     'res_country_group_id', 'pricelist_id', string='Pricelists')


class PricelistItem(models.Model):
    _name = "product.pricelist.item"
    _description = "Pricelist Rule"
    _order = "applied_on, min_quantity desc, categ_id desc, id desc"
    _check_company_auto = True
    # NOTE: if you change _order on this model, make sure it matches the SQL
    # query built in _compute_price_rule() above in this file to avoid
    # inconstencies and undeterministic issues.

    def _default_pricelist_id(self):
        return self.env['product.pricelist'].search([
            '|', ('company_id', '=', False),
            ('company_id', '=', self.env.company.id)], limit=1)

    product_tmpl_id = fields.Many2one(
        'product.template', 'Product', ondelete='cascade', check_company=True,
        help="Specify a template if this rule only applies to one product template. Keep empty otherwise.")
    product_id = fields.Many2one(
        'product.product', 'Product Variant', ondelete='cascade', check_company=True,
        help="Specify a product if this rule only applies to one product. Keep empty otherwise.")
    categ_id = fields.Many2one(
        'product.category', 'Product Category', ondelete='cascade',
        help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")
    min_quantity = fields.Float(
        'Min. Quantity', default=0, digits="Product Unit Of Measure",
        help="For the rule to apply, bought/sold quantity must be greater "
             "than or equal to the minimum quantity specified in this field.\n"
             "Expressed in the default unit of measure of the product.")
    applied_on = fields.Selection([
        ('3_global', 'All Products'),
        ('2_product_category', ' Product Category'),
        ('1_product', 'Product'),
        ('0_product_variant', 'Product Variant')], "Apply On",
        default='3_global', required=True,
        help='Pricelist Item applicable on selected option')
    base = fields.Selection([
        ('list_price', 'Sales Price'),
        ('standard_price', 'Cost'),
        ('pricelist', 'Other Pricelist')], "Based on",
        default='list_price', required=True,
        help='Base price for computation.\n'
             'Sales Price: The base price will be the Sales Price.\n'
             'Cost Price : The base price will be the cost price.\n'
             'Other Pricelist : Computation of the base price based on another Pricelist.')
    base_pricelist_id = fields.Many2one('product.pricelist', 'Other Pricelist', check_company=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', index=True, ondelete='cascade', required=True, default=_default_pricelist_id)
    price_surcharge = fields.Float(
        'Price Surcharge', digits='Product Price',
        help='Specify the fixed amount to add or substract(if negative) to the amount calculated with the discount.')
    price_discount = fields.Float('Price Discount', default=0, digits=(16, 2))
    price_round = fields.Float(
        'Price Rounding', digits='Product Price',
        help="Sets the price so that it is a multiple of this value.\n"
             "Rounding is applied after the discount and before the surcharge.\n"
             "To have prices that end in 9.99, set rounding 10, surcharge -0.01")
    price_min_margin = fields.Float(
        'Min. Price Margin', digits='Product Price',
        help='Specify the minimum amount of margin over the base price.')
    price_max_margin = fields.Float(
        'Max. Price Margin', digits='Product Price',
        help='Specify the maximum amount of margin over the base price.')
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True, related='pricelist_id.company_id', store=True)
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        readonly=True, related='pricelist_id.currency_id', store=True)
    active = fields.Boolean(
        readonly=True, related="pricelist_id.active", store=True)
    date_start = fields.Date('Start Date', help="Starting date for the pricelist rule validation")
    date_end = fields.Date('End Date', help="Ending valid for the pricelist rule validation")
    compute_price = fields.Selection([
        ('fixed', 'Fixed Price'),
        ('percentage', 'Percentage (discount)'),
        ('formula', 'Formula')], index=True, default='fixed', required=True)
    fixed_price = fields.Float('Fixed Price', digits='Product Price')
    percent_price = fields.Float('Percentage Price')
    # functional fields used for usability purposes
    name = fields.Char(
        'Name', compute='_get_pricelist_item_name_price',
        help="Explicit rule name for this pricelist line.")
    price = fields.Char(
        'Price', compute='_get_pricelist_item_name_price',
        help="Explicit rule name for this pricelist line.")

    @api.constrains('base_pricelist_id', 'pricelist_id', 'base')
    def _check_recursion(self):
        if any(item.base == 'pricelist' and item.pricelist_id and item.pricelist_id == item.base_pricelist_id for item in self):
            raise ValidationError(_('You cannot assign the Main Pricelist as Other Pricelist in PriceList Item'))
        return True

    @api.constrains('price_min_margin', 'price_max_margin')
    def _check_margin(self):
        if any(item.price_min_margin > item.price_max_margin for item in self):
            raise ValidationError(_('The minimum margin should be lower than the maximum margin.'))
        return True

    @api.constrains('product_id', 'product_tmpl_id', 'categ_id')
    def _check_product_consistency(self):
        for item in self:
            if item.applied_on == "2_product_category" and not item.categ_id:
                raise ValidationError(_("Please specify the category for which this rule should be applied"))
            elif item.applied_on == "1_product" and not item.product_tmpl_id:
                raise ValidationError(_("Please specify the product for which this rule should be applied"))
            elif item.applied_on == "0_product_variant" and not item.product_id:
                raise ValidationError(_("Please specify the product variant for which this rule should be applied"))

    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        for item in self:
            if item.categ_id and item.applied_on == '2_product_category':
                item.name = _("Category: %s") % (item.categ_id.display_name)
            elif item.product_tmpl_id and item.applied_on == '1_product':
                item.name = _("Product: %s") % (item.product_tmpl_id.display_name)
            elif item.product_id and item.applied_on == '0_product_variant':
                item.name = _("Variant: %s") % (item.product_id.with_context(display_default_code=False).display_name)
            else:
                item.name = _("All Products")

            if item.compute_price == 'fixed':
                decimal_places = self.env['decimal.precision'].precision_get('Product Price')
                if item.currency_id.position == 'after':
                    item.price = "%s %s" % (
                        float_repr(
                            item.fixed_price,
                            decimal_places,
                        ),
                        item.currency_id.symbol,
                    )
                else:
                    item.price = "%s %s" % (
                        item.currency_id.symbol,
                        float_repr(
                            item.fixed_price,
                            decimal_places,
                        ),
                    )
            elif item.compute_price == 'percentage':
                item.price = _("%s %% discount") % (item.percent_price)
            else:
                item.price = _("%s %% discount and %s surcharge") % (item.price_discount, item.price_surcharge)

    @api.onchange('compute_price')
    def _onchange_compute_price(self):
        if self.compute_price != 'fixed':
            self.fixed_price = 0.0
        if self.compute_price != 'percentage':
            self.percent_price = 0.0
        if self.compute_price != 'formula':
            self.update({
                'price_discount': 0.0,
                'price_surcharge': 0.0,
                'price_round': 0.0,
                'price_min_margin': 0.0,
                'price_max_margin': 0.0,
            })

    @api.onchange('product_id')
    def _onchange_product_id(self):
        has_product_id = self.filtered('product_id')
        for item in has_product_id:
            item.product_tmpl_id = item.product_id.product_tmpl_id
        if self.env.context.get('default_applied_on', False) == '1_product':
            # If a product variant is specified, apply on variants instead
            # Reset if product variant is removed
            has_product_id.update({'applied_on': '0_product_variant'})
            (self - has_product_id).update({'applied_on': '1_product'})

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        has_tmpl_id = self.filtered('product_tmpl_id')
        for item in has_tmpl_id:
            if item.product_id and item.product_id.product_tmpl_id != item.product_tmpl_id:
                item.product_id = None

    @api.onchange('product_id', 'product_tmpl_id', 'categ_id')
    def _onchane_rule_content(self):
        if not self.user_has_groups('product.group_sale_pricelist') and not self.env.context.get('default_applied_on', False):
            # If advanced pricelists are disabled (applied_on field is not visible)
            # AND we aren't coming from a specific product template/variant.
            variants_rules = self.filtered('product_id')
            template_rules = (self-variants_rules).filtered('product_tmpl_id')
            variants_rules.update({'applied_on': '0_product_variant'})
            template_rules.update({'applied_on': '1_product'})
            (self-variants_rules-template_rules).update({'applied_on': '3_global'})

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('applied_on', False):
                # Ensure item consistency for later searches.
                applied_on = values['applied_on']
                if applied_on == '3_global':
                    values.update(dict(product_id=None, product_tmpl_id=None, categ_id=None))
                elif applied_on == '2_product_category':
                    values.update(dict(product_id=None, product_tmpl_id=None))
                elif applied_on == '1_product':
                    values.update(dict(product_id=None, categ_id=None))
                elif applied_on == '0_product_variant':
                    values.update(dict(categ_id=None))
        return super(PricelistItem, self).create(vals_list)

    def write(self, values):
        if values.get('applied_on', False):
            # Ensure item consistency for later searches.
            applied_on = values['applied_on']
            if applied_on == '3_global':
                values.update(dict(product_id=None, product_tmpl_id=None, categ_id=None))
            elif applied_on == '2_product_category':
                values.update(dict(product_id=None, product_tmpl_id=None))
            elif applied_on == '1_product':
                values.update(dict(product_id=None, categ_id=None))
            elif applied_on == '0_product_variant':
                values.update(dict(categ_id=None))
        res = super(PricelistItem, self).write(values)
        # When the pricelist changes we need the product.template price
        # to be invalided and recomputed.
        self.flush()
        self.invalidate_cache()
        return res

    def _get_base_price(self, product, quantity, uom, date, currency=None):
        self.ensure_one()
        product.ensure_one()
        price = 0.0
        child_rules = []
        currency = currency or self.currency_id
        if self.compute_price == 'fixed':
            price = product.uom_id._compute_price(self.fixed_price, to_unit=uom)
            if currency and currency != self.currency_id:
                price = self.currency_id._convert(
                    from_amount=price,
                    to_currency=currency,
                    company=self.env.company,
                    date=date,
                    round=False
                )
        elif self.base == 'pricelist' and self.base_pricelist_id:
            qty_in_product_uom = uom._compute_quantity(quantity, product.uom_id, round=False)
            price, child_rules = self.base_pricelist_id._compute_price_rule(
                product,
                quantity=qty_in_product_uom,
                uom=product.uom_id,
                currency=currency,
                date=date,
            )[product.id]
        else:
            # if base option is public price take sale price else cost price of product
            # price_compute returns the price in the context UoM, i.e. qty_uom_id
            price = product.price_compute(
                self.base,
                uom=uom,
                date=date,
                currency=currency
            )[product.id]
        return price, child_rules
