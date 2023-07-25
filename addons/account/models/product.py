# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

ACCOUNT_DOMAIN = "[('deprecated', '=', False), ('internal_type','=','other'), ('company_id', '=', current_company_id), ('is_off_balance', '=', False)]"

class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_income_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account",
        domain=ACCOUNT_DOMAIN,
        help="This account will be used when validating a customer invoice.")
    property_account_expense_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account",
        domain=ACCOUNT_DOMAIN,
        help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon accounting with perpetual inventory valuation in which case the expense (Cost of Goods Sold account) is recognized at the customer invoice validation.")

#----------------------------------------------------------
# Products
#----------------------------------------------------------
class ProductTemplate(models.Model):
    _inherit = "product.template"

    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id', help="Default taxes used when selling the product.", string='Customer Taxes',
        domain=[('type_tax_use', '=', 'sale')], default=lambda self: self.env.company.account_sale_tax_id)
    supplier_taxes_id = fields.Many2many('account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id', string='Vendor Taxes', help='Default taxes used when buying the product.',
        domain=[('type_tax_use', '=', 'purchase')], default=lambda self: self.env.company.account_purchase_tax_id)
    property_account_income_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category.")
    property_account_expense_id = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the expense account on the product category will be used.")

    def _get_product_accounts(self):
        return {
            'income': self.property_account_income_id or self.categ_id.property_account_income_categ_id,
            'expense': self.property_account_expense_id or self.categ_id.property_account_expense_categ_id
        }

    def _get_asset_accounts(self):
        res = {}
        res['stock_input'] = False
        res['stock_output'] = False
        return res

    def get_product_accounts(self, fiscal_pos=None):
        accounts = self._get_product_accounts()
        if not fiscal_pos:
            fiscal_pos = self.env['account.fiscal.position']
        return fiscal_pos.map_accounts(accounts)

    @api.constrains('uom_id')
    def _check_uom_not_in_invoice(self):
        self.env['product.template'].flush(['uom_id'])
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


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_product_accounts(self):
        return self.product_tmpl_id._get_product_accounts()

    @api.model
    def _get_tax_included_unit_price(self, company, currency, document_date, document_type,
            is_refund_document=False, product_uom=None, product_currency=None,
            product_price_unit=None, product_taxes=None, fiscal_position=None
        ):
        """ Helper to get the price unit from different models.
            This is needed to compute the same unit price in different models (sale order, account move, etc.) with same parameters.
        """

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
            product_taxes_after_fp = fiscal_position.map_tax(product_taxes)
            flattened_taxes_after_fp = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
            flattened_taxes_before_fp = product_taxes._origin.flatten_taxes_hierarchy()
            taxes_before_included = all(tax.price_include for tax in flattened_taxes_before_fp)

            if set(product_taxes.ids) != set(product_taxes_after_fp.ids) and taxes_before_included:
                taxes_res = flattened_taxes_before_fp.compute_all(
                    product_price_unit,
                    quantity=1.0,
                    currency=currency,
                    product=product,
                    is_refund=is_refund_document,
                )
                product_price_unit = taxes_res['total_excluded']

                if any(tax.price_include for tax in flattened_taxes_after_fp):
                    taxes_res = flattened_taxes_after_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=currency,
                        product=product,
                        is_refund=is_refund_document,
                        handle_price_include=False,
                    )
                    for tax_res in taxes_res['taxes']:
                        tax = self.env['account.tax'].browse(tax_res['id'])
                        if tax.price_include:
                            product_price_unit += tax_res['amount']

        # Apply currency rate.
        if currency != product_currency:
            product_price_unit = product_currency._convert(product_price_unit, currency, company, document_date)

        return product_price_unit
