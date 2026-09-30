from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_sales_prices(self, pricelist_sudo, fiscal_position_sudo, website):
        '''
        Resolution 4/2025 requires us to display both prices on the e-commerce site:
            - Price including taxes
            - Price excluding taxes

        If the website is configured to use tax-included pricing, we calculate the tax-excluded
        price separately. This tax-excluded price is displayed on the shop page (on both list and grid views).
        '''
        prices = super()._get_sales_prices(pricelist_sudo, fiscal_position_sudo, website)

        if (
            website
            and website.company_id.country_code == 'AR'
            and website.l10n_ar_website_sale_show_both_prices
            and website.tax_display == 'tax_included'
        ):
            for template in self:
                price_info = prices[template.id]

                # Store the tax-excluded price in the res for use in showing both prices
                prices[template.id]['l10n_ar_price_tax_excluded'] = template._apply_taxes_to_price(
                    price_info['raw_pricelist_price'],
                    website.currency_id,
                    tax_display='total_excluded',
                )

        return prices

    def _get_price_info(
        self, product_or_template, quantity, uom, website, pricelist, fiscal_position, **kwargs
    ):
        price_info = super()._get_price_info(
            product_or_template, quantity, uom, website, pricelist, fiscal_position, **kwargs
        )

        if (
            website.company_id.country_code == 'AR'
            and website.l10n_ar_website_sale_show_both_prices
            and website.tax_display == 'tax_included'
        ):
            # Store the tax-excluded price in the res for use in showing both prices
            price_info['l10n_ar_price_tax_excluded'] = product_or_template._apply_taxes_to_price(
                price_info['untaxed_price'],
                price_info['currency'],
                product_taxes=price_info['product_taxes'],
                taxes=price_info['taxes'],
                tax_display='total_excluded',
            )

        return price_info
