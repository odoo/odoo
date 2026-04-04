# -*- coding: utf-8 -*-

from difflib import SequenceMatcher

from odoo import api, Command, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import format_amount, frozendict

ACCOUNT_DOMAIN = "['&', ('deprecated', '=', False), ('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card','off_balance'))]"


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
    property_account_expense_id = fields.Many2one('account.account', company_dependent=True, ondelete='restrict',
        string="Expense Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the expense account on the product category will be used.")
    account_tag_ids = fields.Many2many(
        string="Account Tags",
        comodel_name='account.account.tag',
        domain="[('applicability', '=', 'products')]",
        help="Tags to be set on the base and tax journal items created for this product.")
    fiscal_country_codes = fields.Char(compute='_compute_fiscal_country_codes')

    def _get_product_accounts(self):
        return {
            'income': self.property_account_income_id or self._get_category_account('property_account_income_categ_id'),
            'expense': self.property_account_expense_id or self._get_category_account('property_account_expense_categ_id')
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

    def _get_asset_accounts(self):
        res = {}
        res['stock_input'] = False
        res['stock_output'] = False
        return res

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
        self._cr.execute("""
            SELECT prod_template.id
              FROM account_move_line line
              JOIN product_product prod_variant ON line.product_id = prod_variant.id
              JOIN product_template prod_template ON prod_variant.product_tmpl_id = prod_template.id
              JOIN uom_uom template_uom ON prod_template.uom_id = template_uom.id
              JOIN uom_category template_uom_cat ON template_uom.category_id = template_uom_cat.id
              JOIN uom_uom line_uom ON line.product_uom_id = line_uom.id
              JOIN uom_category line_uom_cat ON line_uom.category_id = line_uom_cat.id
             WHERE prod_template.id IN %s
               AND line.parent_state = 'posted'
               AND template_uom_cat.id != line_uom_cat.id
             LIMIT 1
        """, [tuple(self.ids)])
        if self._cr.fetchall():
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
        for sub_ids in self.env.cr.split_for_in_conditions(self.ids, size=10000):
            chunk = self.browse(sub_ids)
            chunk.write({'taxes_id': links})
            chunk.invalidate_recordset(['taxes_id'])

    def _force_default_purchase_tax(self, companies):
        default_supplier_taxes = companies.filtered('account_purchase_tax_id').account_purchase_tax_id
        if not default_supplier_taxes:
            return
        links = [Command.link(t.id) for t in default_supplier_taxes]
        for sub_ids in self.env.cr.split_for_in_conditions(self.ids, size=10000):
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


class ProductProduct(models.Model):
    _inherit = "product.product"

    tax_string = fields.Char(compute='_compute_tax_string')

    def _get_product_accounts(self):
        return self.product_tmpl_id._get_product_accounts()

    def _get_tax_included_unit_price(self, company, currency, document_date, document_type,
        is_refund_document=False, product_uom=None, product_currency=None,
        product_price_unit=None, product_taxes=None, fiscal_position=None
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
                product_taxes = product.taxes_id.filtered(lambda x: x.company_id == company)
            elif document_type == 'purchase':
                product_taxes = product.supplier_taxes_id.filtered(lambda x: x.company_id == company)
        # Apply unit of measure.
        if product_uom and product.uom_id != product_uom:
            product_price_unit = product.uom_id._compute_price(product_price_unit, product_uom)

        # Apply fiscal position.
        if product_taxes and fiscal_position:
            product_price_unit = self._get_tax_included_unit_price_from_price(
                product_price_unit,
                product_taxes,
                fiscal_position=fiscal_position,
            )

        # Apply currency rate.
        if currency != product_currency:
            product_price_unit = product_currency._convert(product_price_unit, currency, company, document_date, round=False)

        return product_price_unit

    def _get_tax_included_unit_price_from_price(
        self, product_price_unit, product_taxes,
        fiscal_position=None,
        product_taxes_after_fp=None,
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
        )

    @api.depends('lst_price', 'product_tmpl_id', 'taxes_id')
    @api.depends_context('company')
    def _compute_tax_string(self):
        for record in self:
            record.tax_string = record.product_tmpl_id._construct_tax_string(record.lst_price)

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

    def _import_retrieve_product_from_name(self, product_values):

        name = product_values.get('name')
        if not name:
            return

        def find_product_by_name_similarity(values):
            """ Returns the first product whose name similarity ratio with the provided name is at least 90%. """

            # Get similarity threshold from system parameter, fallback to 0.9 if missing, invalid, or out of range (0, 1].
            try:
                similarity_threshold = float(
                    self.env['ir.config_parameter'].sudo().get_param('account.product_name_similarity_threshold', '0.9')
                )
                if similarity_threshold <= 0.0 or similarity_threshold > 1.0:
                    similarity_threshold = 0.9
            except ValueError:
                similarity_threshold = 0.9

            products = self.search(
                expression.AND([
                    [('name', 'ilike', name)],
                    values['static_domain'],
                ]),
            )
            for product in products:
                if SequenceMatcher(None, name.lower(), product.name.lower()).ratio() >= similarity_threshold:
                    return product

        if name and '\n' in name:
            # cut Sales Description from the name
            name = name.split('\n')[0]
        if name:
            return {'criteria': [
                {'domain': [('name', '=', name)]},
                {'search_method': find_product_by_name_similarity},
            ]}

    @api.model
    def _import_retrieve_product_from_invoice_predictive(self, product_values):
        # Check if 'account_accountant' is installed.
        if 'payment_state_before_switch' not in self.env['account.move']._fields:
            return

        invoice_predictive = product_values.get('invoice_predictive')
        if not invoice_predictive:
            return

        def search_predictive(values):
            static_domain = values['static_domain']
            predicted_product_id = self.env['account.move.line']._predict_specific_product(
                move=invoice_predictive['invoice'],
                name=invoice_predictive['name'],
                partner=invoice_predictive['partner'],
            )
            return self.env['product.product'].browse(predicted_product_id).filtered_domain(static_domain)[:1]

        return {
            'criteria': [{
                'search_method': search_predictive,
                'cache_key': frozendict(invoice_predictive),
            }],
        }

    @api.model
    def _import_retrieve_product(self, search_plan, company, product_values_list):
        cache = {}

        static_domain = expression.OR([
            [*self._check_company_domain(company), ('company_id', '!=', False)],
            [('company_id', '=', False)],
        ])
        for product_values in product_values_list:
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

                    product_domain = expression.AND([
                        static_domain,
                        product_extra_domain
                    ])

                    if domain:
                        full_domain = expression.AND([product_domain, domain])
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

    def _retrieve_product(self, name=None, default_code=None, barcode=None, company=None, extra_domain=None):
        '''Search all products and find one that matches one of the parameters.

        :param name:            The name of the product.
        :param default_code:    The default_code of the product.
        :param barcode:         The barcode of the product.
        :param company:         The company of the product.
        :param extra_domain:    Any extra domain to add to the search.
        :returns:               A product or an empty recordset if not found.
        '''
        product_values = {
            'name': name,
            'default_code': default_code,
            'barcode': barcode,
        }
        self._import_retrieve_product(
            search_plan=[
                self._import_retrieve_product_from_barcode,
                self._import_retrieve_product_from_default_code,
                self._import_retrieve_product_from_name,
            ],
            company=company or self.env.company,
            product_values_list=[product_values],
        )
        return product_values.get('product') or self.env['product.product']
