# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductPricelist(models.Model):
    _name = 'product.pricelist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Pricelist"
    _rec_names_search = ['name', 'currency_id']  # TODO check if should be removed
    _order = "sequence, id, name"

    def _default_currency_id(self):
        return self.env.company.currency_id.id

    def _base_domain_item_ids(self):
        return [
            '|', ('product_tmpl_id', '=', None), ('product_tmpl_id.active', '=', True),
            '|', ('product_id', '=', None), ('product_id.active', '=', True),
        ]

    def _domain_item_ids(self):
        return self._base_domain_item_ids()

    name = fields.Char(string="Pricelist Name", required=True, translate=True)

    active = fields.Boolean(
        string="Active",
        default=True,
        help="If unchecked, it will allow you to hide the pricelist without removing it.")
    sequence = fields.Integer(default=16)

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        default=_default_currency_id,
        required=True,
        tracking=1,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        tracking=5,
        default=lambda self: self.env.company,
    )

    country_group_ids = fields.Many2many(
        comodel_name='res.country.group',
        relation='res_country_group_pricelist_rel',
        column1='pricelist_id',
        column2='res_country_group_id',
        string="Country Groups",
        tracking=10,
    )

    item_ids = fields.One2many(
        comodel_name='product.pricelist.item',
        inverse_name='pricelist_id',
        string="Pricelist Rules",
        # must be given as lambda for overrides to work
        domain=lambda self: self._domain_item_ids(),
        copy=True)

    @api.depends('currency_id')
    def _compute_display_name(self):
        for pricelist in self:
            pricelist_name = pricelist.name and pricelist.name or _('New')
            pricelist.display_name = f'{pricelist_name} ({pricelist.currency_id.name})'

    def write(self, vals):
        res = super().write(vals)

        # Make sure that there is no multi-company issue in the existing rules after the company
        # change.
        if 'company_id' in vals and len(self) == 1:
            self.item_ids._check_company()

        return res

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for pricelist, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", pricelist.name)
        return vals_list

    def _get_products_price(self, products, *args, **kwargs):
        """Compute the pricelist prices for the specified products, quantity & uom.

        Note: self and self.ensure_one()

        :param products: recordset of products (product.product/product.template)
        :param float quantity: quantity of products requested (in given uom)
        :param currency: record of currency (res.currency) (optional)
        :param uom: unit of measure (uom.uom record) (optional)
            If not specified, prices returned are expressed in product uoms
        :param date: date to use for price computation and currency conversions (optional)
        :type date: date or datetime

        :returns: {product_id: product price}, considering the current pricelist if any
        :rtype: dict(int, float)
        """
        self and self.ensure_one()  # self is at most one record
        return {
            product_id: res_tuple[0]
            for product_id, res_tuple in self._compute_price_rule(products, *args, **kwargs).items()
        }

    def _get_product_price(self, product, *args, **kwargs):
        """Compute the pricelist price for the specified product, qty & uom.

        Note: self and self.ensure_one()

        :param product: product record (product.product/product.template)
        :param float quantity: quantity of products requested (in given uom)
        :param currency: record of currency (res.currency) (optional)
        :param uom: unit of measure (uom.uom record) (optional)
            If not specified, prices returned are expressed in product uoms
        :param date: date to use for price computation and currency conversions (optional)
        :type date: date or datetime

        :returns: unit price of the product, considering pricelist rules if any
        :rtype: float
        """
        self and self.ensure_one()  # self is at most one record
        return self._compute_price_rule(product, *args, **kwargs)[product.id][0]

    def _get_product_price_rule(self, product, *args, **kwargs):
        """Compute the pricelist price & rule for the specified product, qty & uom.

        Note: self and self.ensure_one()

        :param product: product record (product.product/product.template)
        :param float quantity: quantity of products requested (in given uom)
        :param currency: record of currency (res.currency) (optional)
        :param uom: unit of measure (uom.uom record) (optional)
            If not specified, prices returned are expressed in product uoms
        :param date: date to use for price computation and currency conversions (optional)
        :type date: date or datetime

        :returns: (product unit price, applied pricelist rule id)
        :rtype: tuple(float, int)
        """
        self and self.ensure_one()  # self is at most one record
        return self._compute_price_rule(product, *args, **kwargs)[product.id]

    def _get_product_rule(self, product, *args, **kwargs):
        """Compute the pricelist price & rule for the specified product, qty & uom.

        Note: self and self.ensure_one()

        :param product: product record (product.product/product.template)
        :param float quantity: quantity of products requested (in given uom)
        :param currency: record of currency (res.currency) (optional)
        :param uom: unit of measure (uom.uom record) (optional)
            If not specified, prices returned are expressed in product uoms
        :param date: date to use for price computation and currency conversions (optional)
        :type date: date or datetime

        :returns: applied pricelist rule id
        :rtype: int or False
        """
        self and self.ensure_one()  # self is at most one record
        return self._compute_price_rule(product, *args, compute_price=False, **kwargs)[product.id][1]

    def _compute_price_rule(
        self, products, quantity, *, currency=None, uom=None, date=False, compute_price=True,
        **kwargs
    ):
        """ Low-level method - Mono pricelist, multi products
        Returns: dict{product_id: (price, suitable_rule) for the given pricelist}

        Note: self and self.ensure_one()

        :param products: recordset of products (product.product/product.template)
        :param float quantity: quantity of products requested (in given uom)
        :param currency: record of currency (res.currency)
                         note: currency.ensure_one()
        :param uom: unit of measure (uom.uom record)
            If not specified, prices returned are expressed in product uoms
        :param date: date to use for price computation and currency conversions
        :type date: date or datetime
        :param bool compute_price: whether the price should be computed (default: True)

        :returns: product_id: (price, pricelist_rule)
        :rtype: dict
        """
        self and self.ensure_one()  # self is at most one record

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()

        if not products:
            return {}

        if not date:
            # Used to fetch pricelist rules and currency rates
            date = fields.Datetime.now()

        # Fetch all rules potentially matching specified products/templates/categories and date
        rules = self._get_applicable_rules(products, date, **kwargs)

        results = {}
        for product in products:
            suitable_rule = self.env['product.pricelist.item']

            product_uom = product.uom_id
            target_uom = uom or product_uom  # If no uom is specified, fall back on the product uom

            # Compute quantity in product uom because pricelist rules are specified
            # w.r.t product default UoM (min_quantity, price_surchage, ...)
            if target_uom != product_uom:
                qty_in_product_uom = target_uom._compute_quantity(
                    quantity, product_uom, raise_if_failure=False
                )
            else:
                qty_in_product_uom = quantity

            for rule in rules:
                if rule._is_applicable_for(product, qty_in_product_uom):
                    suitable_rule = rule
                    break

            if compute_price:
                price = suitable_rule._compute_price(
                    product, quantity, target_uom, date=date, currency=currency, **kwargs)
            else:
                # Skip price computation when only the rule is requested.
                price = 0.0

            results[product.id] = (price, suitable_rule.id)

        return results

    # Split methods to ease (community) overrides
    def _get_applicable_rules(self, products, date, **kwargs):
        self and self.ensure_one()  # self is at most one record
        if not self:
            return self.env['product.pricelist.item']

        return self.env['product.pricelist.item'].search(
            self._get_applicable_rules_domain(products=products, date=date, **kwargs)
        )

    def _get_applicable_rules_domain(self, products, date, **kwargs):
        self and self.ensure_one()  # self is at most one record
        if products._name == 'product.template':
            templates_domain = ('product_tmpl_id', 'in', products.ids)
            products_domain = ('product_id.product_tmpl_id', 'in', products.ids)
        else:
            templates_domain = ('product_tmpl_id', 'in', products.product_tmpl_id.ids)
            products_domain = ('product_id', 'in', products.ids)

        return [
            ('pricelist_id', '=', self.id),
            '|', ('categ_id', '=', False), ('categ_id', 'parent_of', products.categ_id.ids),
            '|', ('product_tmpl_id', '=', False), templates_domain,
            '|', ('product_id', '=', False), products_domain,
            '|', ('date_start', '=', False), ('date_start', '<=', date),
            '|', ('date_end', '=', False), ('date_end', '>=', date),
        ]

    # Multi pricelists price|rule computation
    def _price_get(self, product, quantity, **kwargs):
        """ Multi pricelist, mono product - returns price per pricelist """
        return {
            key: price[0]
            for key, price in self._compute_price_rule_multi(product, quantity, **kwargs)[product.id].items()}

    def _compute_price_rule_multi(self, products, quantity, uom=None, date=False, **kwargs):
        """ Low-level method - Multi pricelist, multi products
        Returns: dict{product_id: dict{pricelist_id: (price, suitable_rule)} }"""
        if not self.ids:
            pricelists = self.search([])
        else:
            pricelists = self
        results = {}
        for pricelist in pricelists:
            subres = pricelist._compute_price_rule(products, quantity, uom=uom, date=date, **kwargs)
            for product_id, price in subres.items():
                results.setdefault(product_id, {})
                results[product_id][pricelist.id] = price
        return results

    def _get_country_pricelist_multi(self, country_ids):
        def get_param_id(key):
            string_value = self.env['ir.config_parameter'].sudo().get_param(key, False)
            try:
                return int(string_value)
            except (TypeError, ValueError, OverflowError):
                return None

        company_id = self.env.company.id
        pl_domain = self._get_partner_pricelist_multi_search_domain_hook(company_id)

        if (
            (ctx_code := self.env.context.get('country_code'))
            and (ctx_country := self.env['res.country'].search([('code', '=', ctx_code)], limit=1))
        ):
            if ctx_country.id not in country_ids:
                country_ids.append(ctx_country.id)
        else:
            ctx_country = False

        # get fallback pricelist when no pricelist for a given country
        pl_fallback = (
            self.search(pl_domain + [('country_group_ids', '=', False)], limit=1)
            # save data in ir.config_parameter instead of ir.default for
            # res.partner.property_product_pricelist
            # otherwise the data will become the default value while
            # creating without specifying the property_product_pricelist
            # however if the property_product_pricelist is not specified
            # the result of the previous line should have high priority
            # when computing
            or self.browse(get_param_id(f'res.partner.property_product_pricelist_{company_id}'))
            or self.browse(get_param_id('res.partner.property_product_pricelist'))
            or self.search(pl_domain, limit=1)
        )
        result = {}
        for country_id in country_ids:
            pl = self.search([
                *pl_domain,
                ('country_group_ids.country_ids', '=', country_id),
            ], limit=1)
            result[country_id] = pl or pl_fallback
        result[False] = result[ctx_country.id] if ctx_country else pl_fallback
        return result

    # res.partner.property_product_pricelist field computation
    @api.model
    def _get_partner_pricelist_multi(self, partner_ids):
        """ Retrieve the applicable pricelist for given partners in a given company.

        It will return the first found pricelist in this order:
        First, the pricelist of the specific property (res_id set), this one
                is created when saving a pricelist on the partner form view.
        Else, it will return the pricelist of the partner country group
        Else, it will return the generic property (res_id not set)
        Else, it will return the first available pricelist if any

        :return: a dict {partner_id: pricelist}
        """
        ProductPricelist = self.env['product.pricelist']

        if not self.env['res.groups']._is_feature_enabled('product.group_product_pricelist'):
            # Skip pricelist computation if pricelists are disabled.
            return defaultdict(lambda: ProductPricelist)

        # `partner_ids` might be ID from inactive users. We should use active_test
        # as we will do a search() later (real case for website public user).
        Partner = self.env['res.partner'].with_context(active_test=False)

        # if no specific property, try to find a fitting pricelist
        result = {}
        remaining_partner_ids = []
        for partner in Partner.browse(partner_ids):
            if partner.specific_property_product_pricelist._get_partner_pricelist_multi_filter_hook():
                result[partner.id] = partner.specific_property_product_pricelist
            else:
                remaining_partner_ids.append(partner.id)

        if remaining_partner_ids:
            # group partners by country, and find a pricelist for each country
            remaining_partners = self.env['res.partner'].browse(remaining_partner_ids)
            partners_by_country = remaining_partners.grouped('country_id')
            country_ids = remaining_partners.country_id.ids
            pricelists_by_country_id = self._get_country_pricelist_multi(country_ids)
            for country, partners in partners_by_country.items():
                pl = pricelists_by_country_id[country.id]
                result.update(dict.fromkeys(partners._ids, pl))

        return result

    def _get_partner_pricelist_multi_search_domain_hook(self, company_id):
        return [
            ('active', '=', True),
            ('company_id', 'in', [company_id, False]),
        ]

    def _get_partner_pricelist_multi_filter_hook(self):
        return self.filtered('active')

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Pricelists'),
            'template': '/product/static/xls/product_pricelist.xls'
        }]

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_as_rule_base(self):
        linked_items = self.env['product.pricelist.item'].sudo().search([
            ('base', '=', 'pricelist'),
            ('base_pricelist_id', 'in', self.ids),
            ('pricelist_id', 'not in', self.ids),
        ])
        if linked_items:
            raise UserError(_(
                'You cannot delete pricelist(s):\n(%(pricelists)s)\nThey are used within pricelist(s):\n%(other_pricelists)s',
                pricelists='\n'.join(linked_items.base_pricelist_id.mapped('display_name')),
                other_pricelists='\n'.join(linked_items.pricelist_id.mapped('display_name')),
            ))

    @api.readonly
    def action_open_pricelist_report(self):
        self.ensure_one()
        return {
            'name': _("Pricelist Report Preview"),
            'type': 'ir.actions.client',
            'tag': 'generate_pricelist_report',
        }
