from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_sales_prices(self, pricelist_sudo, fiscal_position_sudo, website):
        prices = super()._get_sales_prices(pricelist_sudo, fiscal_position_sudo, website)
        if (
            website
            and website.company_id.country_code == 'AR'
            and website.l10n_ar_website_sale_show_both_prices
            and website.show_line_subtotals_tax_selection == 'tax_included'
        ):
            for product in self:
                prices[product.id]['l10n_ar_price_tax_excluded'] = product._apply_taxes_to_price(
                    prices[product.id]['raw_pricelist_price'],
                    website.currency_id,
                    tax_display='total_excluded',
                )
        return prices
