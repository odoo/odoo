# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_product_accounts(self):
        accounts = super()._get_product_accounts()
        if self.categ_id:
            # If category set on the product take production account from category even if
            # production account on category is False
            production_account = self.categ_id.property_stock_account_production_cost_id
        else:
            ProductCategory = self.env['product.category']
            production_account = (
                self.valuation == 'real_time'
                and ProductCategory._fields['property_stock_account_production_cost_id'].get_company_dependent_fallback(
                    ProductCategory
                )
                or self.env['account.account']
            )
        accounts['production'] = production_account
        return accounts


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_value(self):
        """
        Exclude kit products from inventory valuation to avoid double counting.
        Only non-kit products are valuated; kits are set to zero value.
        """
        non_kit_products = self.filtered(lambda product: not product.is_kits)
        super(ProductProduct, non_kit_products)._compute_value()
        kit_products = self - non_kit_products
        for kit_product in kit_products:
            kit_product.company_currency_id = kit_product.company_id.currency_id or self.env.company.currency_id
            kit_product.total_value = 0.0
            kit_product.avg_cost = 0.0


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_stock_account_production_cost_id = fields.Many2one(
        'account.account', 'Production Account', company_dependent=True, ondelete='restrict',
        check_company=True,
        help="""This account will be used as a valuation counterpart for both components and final products for manufacturing orders.
                If there are any workcenter/employee costs, this value will remain on the account once the production is completed.""")
