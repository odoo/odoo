from difflib import SequenceMatcher

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import format_amount, frozendict
from odoo.tools.misc import split_every
from odoo.tools.constants import IN_MAX

ACCOUNT_DOMAIN = "[('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card','off_balance'))]"


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_income_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account",
        domain=ACCOUNT_DOMAIN,
        help="This account will be used when validating a customer invoice.",
        tracking=True,
        ondelete='restrict',
    )
    property_account_expense_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account",
        domain=ACCOUNT_DOMAIN,
        help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon accounting with perpetual inventory valuation in which case the expense (Cost of Goods Sold account) is recognized at the customer invoice validation.",
        tracking=True,
        ondelete='restrict',
    )
    property_valuation = fields.Selection(
        string="Inventory Valuation",
        selection=[
            ('periodic', 'Periodic (at closing)'),
            ('real_time', 'Perpetual (at invoicing)'),
        ],
        company_dependent=True, copy=True, tracking=True,
        help="""Periodic: The accounting entries are suggested manually in the inventory valuation report.
        Perpetual: An accounting entry is automatically created to value the inventory when a product is billed or invoiced.
        """)
    property_stock_valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="""When automated inventory valuation is enabled on a product, this account will hold the current value of the products.""")
    property_stock_valuation_account_active = fields.Boolean(related='property_stock_valuation_account_id.active', string="Stock Valuation Account Active")
    property_stock_journal = fields.Many2one(
        'account.journal', 'Stock Journal', company_dependent=True,
        help="When doing automated inventory valuation, this is the Accounting Journal in which entries will be automatically posted when stock moves are processed.")
    account_stock_variation_id = fields.Many2one(
        'account.account', string="Stock Variation Account", readonly=False,
        related="property_stock_valuation_account_id.account_stock_variation_id")
    account_stock_variation_active = fields.Boolean(related='account_stock_variation_id.active', string="Stock Variation Account Active")

#----------------------------------------------------------
# Products
#----------------------------------------------------------


class ProductTemplate(models.Model):
    _inherit = "product.template"

    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id',
        string="Sales Taxes",
        help="Default taxes used when selling the product",
        domain=[('type_tax_use', '=', 'sale')],
        default=lambda self: self.env.companies.account_sale_tax_id or self.env.companies.root_id.sudo().account_sale_tax_id,
    )
    tax_string = fields.Char(compute='_compute_tax_string')
    supplier_taxes_id = fields.Many2many('account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id',
        string="Purchase Taxes",
        help="Default taxes used when buying the product",
        domain=[('type_tax_use', '=', 'purchase')],
        default=lambda self: self.env.companies.account_purchase_tax_id or self.env.companies.root_id.sudo().account_purchase_tax_id,
    )
    property_account_income_id = fields.Many2one('account.account', company_dependent=True, ondelete='restrict',
        string="Income Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category.")
    property_account_income_active = fields.Boolean(related='property_account_income_id.active', string="Income Account Active")
    property_account_expense_id = fields.Many2one('account.account', company_dependent=True, ondelete='restrict',
        string="Expense Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the expense account on the product category will be used.")
    property_account_expense_active = fields.Boolean(related='property_account_expense_id.active', string="Expense Account Active")
    account_tag_ids = fields.Many2many(
        string="Account Tags",
        comodel_name='account.account.tag',
        domain="[('applicability', '=', 'products')]",
        help="Tags to be set on the base and tax journal items created for this product.")
    fiscal_country_codes = fields.Char(compute='_compute_fiscal_country_codes')
    valuation = fields.Selection(
        string="Valuation",
        selection=[
            ('periodic', 'Periodic (at closing)'),
            ('real_time', 'Perpetual (at invoicing)'),
        ],
        compute='_compute_valuation', search='_search_valuation',
    )

    def _get_product_accounts(self):
        return {
            'income': (
                self.property_account_income_id
                or self._get_category_account('property_account_income_categ_id')
                or (self.company_id or self.env.company).income_account_id
            ), 'expense': (
                self.property_account_expense_id
                or self._get_category_account('property_account_expense_categ_id')
                or (self.company_id or self.env.company).expense_account_id
            ), 'stock_valuation': (
                self._get_category_account('property_stock_valuation_account_id')
                or (self.company_id or self.env.company).account_stock_valuation_id
            ),
        }

    def _get_category_account(self, field_name):
        """
        Return the first account defined on the product category hierarchy
        for the given field.
        """
        categ = self.categ_id
        while categ:
            account = categ[field_name]
            if account:
                return account
            categ = categ.parent_id
        return self.env['account.account']

    def get_product_accounts(self, fiscal_pos=None):
        return {
            key: (fiscal_pos or self.env['account.fiscal.position']).map_account(account)
            for key, account in self._get_product_accounts().items()
        }

    @api.depends('company_id')
    @api.depends_context('allowed_company_ids')
    def _compute_fiscal_country_codes(self):
        for record in self:
            allowed_companies = record.company_id or self.env.companies
            record.fiscal_country_codes = ",".join(allowed_companies.mapped('account_fiscal_country_id.code'))

    def _search_valuation(self, operator, value):
        if operator != '=':
            raise UserError(self.env._("You can only use the '=' operator to search on valuation field."))
        if value not in ['periodic', 'real_time']:
            raise UserError(self.env._("Only the value 'periodic' and 'real_time' are accepted to search on valuation field."))
        domain_categ = Domain([('categ_id.property_valuation', operator, value)])
        domain_company = Domain(['|', ('categ_id.property_valuation', '=', False), ('categ_id', '=', False), ('company_id.inventory_valuation', operator, value)])

        if self.env.company.inventory_valuation and self.env.company.inventory_valuation == value:
            domain_company = Domain(['|', ('categ_id.property_valuation', '=', False), ('categ_id', '=', False), '|', ('company_id.inventory_valuation', operator, value), ('company_id', '=', False)])
        return Domain([('is_storable', '=', True)]) & (domain_company | domain_categ)

    @api.depends_context('company')
    @api.depends('is_storable', 'categ_id.property_valuation')
    def _compute_valuation(self):
        for product_template in self:
            if not product_template.is_storable:
                product_template.valuation = False
                continue
            company = product_template.company_id
            if not company or self.env.company.filtered_domain([('id', 'child_of', company.id)]):
                company = self.env.company
            product_template.valuation = product_template.categ_id.with_company(company).property_valuation or company.inventory_valuation

    @api.depends('taxes_id', 'list_price')
    @api.depends_context('company')
    def _compute_tax_string(self):
        for record in self:
            record.tax_string = record._construct_tax_string(record.list_price)

    def _construct_tax_string(self, price):
        currency = self.currency_id
        res = self.taxes_id._filter_taxes_by_company(self.env.company).compute_all(
            price, product=self, partner=self.env['res.partner']
        )
        joined = []
        included = res['total_included']
        if currency.compare_amounts(included, price):
            joined.append(_('%(amount)s Incl. Taxes', amount=format_amount(self.env, included, currency)))
        excluded = res['total_excluded']
        if currency.compare_amounts(excluded, price):
            joined.append(_('%(amount)s Excl. Taxes', amount=format_amount(self.env, excluded, currency)))
        if joined:
            tax_string = f"(= {', '.join(joined)})"
        else:
            tax_string = " "
        return tax_string

    @api.constrains('uom_id')
    def _check_uom_not_in_invoice(self):
        self.env['product.template'].flush_model(['uom_id'])
        self.env.cr.execute("""
            SELECT prod_template.id
              FROM account_move_line line
              JOIN product_product prod_variant ON line.product_id = prod_variant.id
              JOIN product_template prod_template ON prod_variant.product_tmpl_id = prod_template.id
              JOIN uom_uom template_uom ON prod_template.uom_id = template_uom.id
              JOIN uom_uom line_uom ON line.product_uom_id = line_uom.id
             WHERE prod_template.id IN %s
               AND line.parent_state = 'posted'
               AND template_uom.id != line_uom.id
             LIMIT 1
        """, [tuple(self.ids)])
        if self.env.cr.fetchall():
            raise ValidationError(_(
                "This product is already being used in posted Journal Entries.\n"
                "If you want to change its Unit of Measure, please archive this product and create a new one."
            ))

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'combo':
            self.taxes_id = False
            self.supplier_taxes_id = False
        return super()._onchange_type()

    def _force_default_sale_tax(self, companies):
        default_customer_taxes = companies.filtered('account_sale_tax_id').account_sale_tax_id
        if not default_customer_taxes:
            return
        links = [Command.link(t.id) for t in default_customer_taxes]
        for sub_ids in split_every(IN_MAX, self.ids):
            chunk = self.browse(sub_ids)
            chunk.write({'taxes_id': links})
            chunk.invalidate_recordset(['taxes_id'])

    def _force_default_purchase_tax(self, companies):
        default_supplier_taxes = companies.filtered('account_purchase_tax_id').account_purchase_tax_id
        if not default_supplier_taxes:
            return
        links = [Command.link(t.id) for t in default_supplier_taxes]
        for sub_ids in split_every(IN_MAX, self.ids):
            chunk = self.browse(sub_ids)
            chunk.write({'supplier_taxes_id': links})
            chunk.invalidate_recordset(['supplier_taxes_id'])

    def _force_default_tax(self, companies):
        self._force_default_sale_tax(companies)
        self._force_default_purchase_tax(companies)

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        # If no company was set for the product, the product will be available for all companies and therefore should
        # have the default taxes of the other companies as well. sudo() is used since we're going to need to fetch all
        # the other companies default taxes which the user may not have access to.
        other_companies = self.env['res.company'].sudo().search(['!', ('id', 'child_of', self.env.companies.ids)])
        if other_companies and products:
            products_without_company = products.filtered(lambda p: not p.company_id).sudo()
            products_without_company._force_default_tax(other_companies)
        return products

    def _get_list_price(self, price):
        """ Get the product sales price from a public price based on taxes defined on the product """
        self.ensure_one()
        if not self.taxes_id:
            return super()._get_list_price(price)
        computed_price = self.taxes_id.compute_all(price, self.currency_id)
        total_included = computed_price["total_included"]

        if price == total_included:
            # Tax is configured as price included
            return total_included
        # calculate base from tax
        included_computed_price = self.taxes_id.with_context(force_price_include=True).compute_all(price, self.currency_id)
        return included_computed_price['total_excluded']

    def _get_price_diff_account(self):
        self.ensure_one()
        return False


class ProductProduct(models.Model):
    _inherit = "product.product"

    catalog_is_in_selected_section = fields.Boolean(
        search="_search_is_in_selected_catalog_section", store=False
    )
    tax_string = fields.Char(compute='_compute_tax_string')

    def _search_is_in_selected_catalog_section(self, operator, value):
        if operator != 'in':
            return NotImplemented

        ctx = self.env.context
        order_id = ctx.get('order_id')
        order_model = ctx.get('product_catalog_order_model')
        line_field = ctx.get('child_field')
        if not (order_id and order_model and line_field):
            return []

        order_lines = self.env[order_model].browse(order_id)[line_field]
        product_ids = order_lines.filtered(lambda line: line._is_in_section()).product_id.ids

        return [('id', 'in', product_ids)]

    def _get_product_accounts(self):
        return self.product_tmpl_id._get_product_accounts()

    def _get_tax_included_unit_price(self, company, currency, document_date, document_type,
        is_refund_document=False, product_uom=None, product_currency=None,
        product_price_unit=None, product_taxes=None, fiscal_position=None,
        document_tax_mode=None,
    ):
        """ Helper to get the price unit from different models.
            This is needed to compute the same unit price in different models (sale order, account move, etc.) with same parameters.
        """
        self.ensure_one()
        company.ensure_one()

        product = self

        assert document_type

        if product_uom is None:
            product_uom = product.uom_id
        if not product_currency:
            if document_type == 'sale':
                product_currency = product.currency_id
            elif document_type == 'purchase':
                product_currency = company.currency_id
        if product_price_unit is None:
            if document_type == 'sale':
                product_price_unit = product.with_company(company).lst_price
            elif document_type == 'purchase':
                product_price_unit = product.with_company(company).standard_price
            else:
                return 0.0
        if product_taxes is None:
            if document_type == 'sale':
                product_taxes = product.taxes_id
            elif document_type == 'purchase':
                product_taxes = product.supplier_taxes_id
        if product_taxes:
            product_taxes = product_taxes._filter_taxes_by_company(company)
        # Apply unit of measure.
        if product_uom and product.uom_id != product_uom:
            product_price_unit = product.uom_id._compute_price(product_price_unit, product_uom)

        # Apply document tax mode.
        if document_tax_mode:
            product_price_unit = self._adapt_price_unit_to_document_tax_mode(
                product_price_unit,
                product_taxes,
                product_uom,
                document_tax_mode,
            )

        # Apply fiscal position.
        if product_taxes and fiscal_position:
            product_price_unit = self._get_tax_included_unit_price_from_price(
                product_price_unit,
                product_taxes,
                fiscal_position=fiscal_position,
                document_tax_mode=document_tax_mode,
            )

        # Apply currency rate.
        if currency != product_currency:
            product_price_unit = product_currency._convert(product_price_unit, currency, company, document_date, round=False)

        return product_price_unit

    def _get_tax_included_unit_price_from_price(
        self, product_price_unit, product_taxes,
        fiscal_position=None,
        product_taxes_after_fp=None,
        document_tax_mode=None,
    ):
        if not product_taxes:
            return product_price_unit

        if product_taxes_after_fp is None:
            if not fiscal_position:
                return product_price_unit

            product_taxes_after_fp = fiscal_position.map_tax(product_taxes)

        return product_taxes._adapt_price_unit_to_another_taxes(
            price_unit=product_price_unit,
            product=self,
            original_taxes=product_taxes,
            new_taxes=product_taxes_after_fp,
            document_tax_mode=document_tax_mode,
        )

    @api.depends('lst_price', 'product_tmpl_id', 'taxes_id')
    @api.depends_context('company')
    def _compute_tax_string(self):
        for record in self:
            record.tax_string = record.product_tmpl_id._construct_tax_string(record.lst_price)

    @api.model
    def _adapt_price_unit_to_document_tax_mode(
        self,
        product_price_unit,
        product_taxes,
        product_uom,
        document_tax_mode,
    ):
        if document_tax_mode == self.company_id.account_price_include:
            return product_price_unit
        results = product_taxes._get_tax_details(
            price_unit=product_price_unit,
            quantity=1.0,
            rounding_method='round_globally',
            product=self,
            product_uom=product_uom,
            document_tax_mode=self.company_id.account_price_include,
        )
        if document_tax_mode == 'tax_included':
            price_unit = results['total_included']
            for tax in results['taxes_data']:
                if tax['tax'].price_include_override == 'tax_excluded':
                    price_unit -= tax['tax_amount']
        else:
            price_unit = results['total_excluded']
            for tax in results['taxes_data']:
                if tax['tax'].price_include_override == 'tax_included':
                    price_unit += tax['tax_amount']

        return price_unit

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    def _import_retrieve_product_from_barcode(self, product_values):
        barcode = product_values.get('barcode')
        if barcode:
            return {'criteria': [{'domain': [('barcode', '=', barcode)]}]}

    def _import_retrieve_product_from_default_code(self, product_values):
        default_code = product_values.get('default_code')
        if default_code:
            return {'criteria': [{'domain': [('default_code', '=', default_code)]}]}

    def _import_retrieve_product_from_supplierinfo(self, product_values):
        vendor_partner_id = product_values.get('vendor_partner_id')
        if not vendor_partner_id:
            return {}
        product_codes = [
            code for code in [
                product_values.get('sellers_item_id'),
                product_values.get('standard_item_id'),
                product_values.get('buyers_item_id'),
            ]
            if code
        ]
        if not product_codes:
            return {}

        return {
            'criteria': [{
                'domain': [(
                    'product_tmpl_id.seller_ids', 'any', [
                        ('partner_id', '=', vendor_partner_id),
                        ('product_code', 'in', product_codes),
                    ],
                )]
            }]
        }

    def _import_retrieve_product_from_name(self, product_values):

        name = product_values.get('name')
        if not name:
            return

        def find_product_by_name_similarity(values):
            """ Returns the first product whose name similarity ratio with the provided name is at least 90%. """

            # Get similarity threshold from system parameter, fallback to 0.9 if missing, invalid, or out of range (0, 1].
            try:
                similarity_threshold = self.env['ir.config_parameter'].sudo().get_float('account.product_name_similarity_threshold', 0.9)
                if similarity_threshold <= 0.0 or similarity_threshold > 1.0:
                    similarity_threshold = 0.9
            except ValueError:
                similarity_threshold = 0.9

            all_product_ids = self.search(
                Domain.AND([
                    [('name', 'ilike', name)],
                    values['static_domain'],
                ]),
            ).ids
            lowered_name = name.lower()
            for products in split_every(IN_MAX, all_product_ids, self.browse):
                products.fetch(['product_tmpl_id'])
                templates = products.product_tmpl_id
                templates.fetch(['name'])
                for product in products:
                    if SequenceMatcher(None, lowered_name, product.name.lower()).ratio() >= similarity_threshold:
                        return product
                products.invalidate_recordset()
                templates.invalidate_recordset()
            return self.env['product.product']

        if name and '\n' in name:
            # cut Sales Description from the name
            name = name.split('\n')[0]
        if name:
            return {'criteria': [
                {'domain': [('name', '=', name)]},
                {'search_method': find_product_by_name_similarity, 'cache_key': str([('name', '=', name)])},
            ]}

    @api.model
    def _import_retrieve_product(self, search_plan, company, product_values_list):
        cache = {}

        static_domain = Domain.OR([
            [*self._check_company_domain(company), ('company_id', '!=', False)],
            [('company_id', '=', False)],
        ])
        for product_values in product_values_list:
            if product_values.get('product'):
                continue
            product = None
            for plan in search_plan:
                plan_values = plan(product_values)
                if not plan_values:
                    continue

                for criteria in plan_values['criteria']:
                    domain = criteria.get('domain')
                    search_method = criteria.get('search_method')
                    if domain:
                        domain = list(domain)
                        cache_key = str(domain)
                    else:
                        cache_key = criteria.get('cache_key')

                    cache_key = frozendict({
                        'cache_key': cache_key,
                        'intrastat_code': product_values.get('intrastat_code'),
                        'unspsc_code': product_values.get('unspsc_code'),
                        'l10n_ro_cpv_code': product_values.get('l10n_ro_cpv_code'),
                        'cg_item_classification_code': product_values.get('cg_item_classification_code'),
                    })

                    # Look at the cache if the value has already been tested with this key.
                    if cache_key in cache:
                        if product := cache[cache_key]:
                            product_values['product'] = product
                            break
                        else:
                            continue

                    orders = ['company_id', 'id DESC']
                    product_extra_domain = []
                    if (
                        (intrastat_code := product_values.get('intrastat_code'))
                        and 'intrastat_code_id' in self._fields
                        and (intrastat_code_record := self.env['account.intrastat.code'].search([('code', '=', intrastat_code)], limit=1))
                    ):
                        product_extra_domain.append(('intrastat_code_id', 'in', (intrastat_code_record.id, False)))
                        orders.insert(1, 'intrastat_code_id')
                    if (
                        (unspsc_code := product_values.get('unspsc_code'))
                        and 'unspsc_code_id' in self._fields
                        and (unspsc_code_record := self.env['product.unspsc.code'].search([('code', '=', unspsc_code)], limit=1))
                    ):
                        product_extra_domain.append(('unspsc_code_id', 'in', (unspsc_code_record.id, False)))
                        orders.insert(1, 'unspsc_code_id')
                    if (
                        (l10n_ro_cpv_code := product_values.get('l10n_ro_cpv_code'))
                        and 'cpv_code_id' in self._fields
                        and (cpv_code_record := self.env['l10n_ro.cpv.code'].search([('code', '=', l10n_ro_cpv_code)], limit=1))
                    ):
                        product_extra_domain.append(('cpv_code_id', 'in', (cpv_code_record.id, False)))
                        orders.insert(1, 'cpv_code_id')
                    if (
                        (cg_item_classification_code := product_values.get('cg_item_classification_code'))
                        and 'l10n_hr_kpd_category_id' in self._fields
                        and (cpv_code_record := self.env['l10n_hr.kpd.category'].search([('name', '=', cg_item_classification_code)], limit=1))
                    ):
                        product_extra_domain.append(('l10n_hr_kpd_category_id', 'in', (cpv_code_record.id, False)))
                        orders.insert(1, 'l10n_hr_kpd_category_id')

                    product_domain = Domain.AND([
                        static_domain,
                        product_extra_domain
                    ])

                    if domain:
                        full_domain = Domain.AND([product_domain, domain])
                        product = self.search(
                            full_domain,
                            order=', '.join(orders),
                            limit=1,
                        )
                    elif search_method:
                        product = search_method({
                            **criteria,
                            'static_domain': product_domain,
                        })

                    if product:
                        if cache_key:
                            cache[cache_key] = product
                        product_values['product'] = product
                        break

                if product:
                    break

    def _get_retrieval_product_search_plan(self):
        return [
            (5, self._import_retrieve_product_from_supplierinfo),
            (10, self._import_retrieve_product_from_barcode),
            (15, self._import_retrieve_product_from_default_code),
            (20, self._import_retrieve_product_from_name),
        ]

    def _retrieve_product(self, company=None, extra_domain=None, **product_vals):
        '''Search all products and find one that matches one of the parameters.

        :param name:            The name of the product.
        :param default_code:    The default_code of the product.
        :param barcode:         The barcode of the product.
        :param company:         The company of the product.
        :param extra_domain:    Any extra domain to add to the search.
        :returns:               A product or an empty recordset if not found.
        '''
        self._import_retrieve_product(
            search_plan=[method[1] for method in sorted(self._get_retrieval_product_search_plan())],
            company=company or self.env.company,
            product_values_list=[product_vals],
        )
        return product_vals.get('product') or self.env['product.product']

    def _get_product_domain_search_order(self, **vals):
        """Gives the order of search for a product given the parameters.

        :param name:            The name of the product.
        :param default_code:    The default_code of the product.
        :param barcode:         The barcode of the product.
        :returns:               An ordered list of product domains and their associated priority.
        :rtype: list[tuple[int, Domain]]
        """
        sorted_domains = []
        if barcode := vals.get('barcode'):
            sorted_domains.append((5, Domain('barcode', '=', barcode)))
        if default_code := vals.get('default_code'):
            sorted_domains.append((10, Domain('default_code', '=', default_code)))
        if name := vals.get('name'):
            name = name.split('\n', 1)[0]  # Cut sales description from the name
            sorted_domains.append((15, Domain('name', '=ilike', name)))
        return sorted_domains

    def _get_price_diff_account(self):
        return self.product_tmpl_id._get_price_diff_account()
