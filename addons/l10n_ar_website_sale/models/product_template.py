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
            and website.show_line_subtotals_tax_selection == 'tax_included'
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

    def _get_additional_combination_info(
        self, product_or_template, quantity, uom, website, pricelist, fiscal_position
    ):
        combination_info = super()._get_additional_combination_info(
            product_or_template, quantity, uom, website, pricelist, fiscal_position
        )
        if (
            website
            and website.company_id.country_code == 'AR'
            and website.l10n_ar_website_sale_show_both_prices
            and website.show_line_subtotals_tax_selection == 'tax_included'
        ):
<<<<<<< c099f59d7ce3ca115d91191d973558dab42df8db
||||||| 3163227cd86b05422788cc438b553ba1c77c3d52
            # Get applicable taxes for the product and map them using the website's FPOS
            product_taxes = product_or_template.sudo().taxes_id._filter_taxes_by_company(self.env.company)
            mapped_taxes = request.fiscal_position.map_tax(product_taxes)

            # Compute price per unit of product or template
            pricelist_prices = request.pricelist._compute_price_rule(product_or_template, quantity)
            unit_price = pricelist_prices[product_or_template.id][0]

            # Compute the tax-excluded value
            total_excluded_value = mapped_taxes.compute_all(
                price_unit=unit_price,
                currency=website.currency_id,
                product=product_or_template,
            )['total_excluded']

            # Check if a discount is applied and adjust the tax-excluded price accordingly
            if combination_info['has_discounted_price']:
                discount_percent = (combination_info['list_price'] - combination_info['price']) / combination_info['list_price']
                total_excluded_value = total_excluded_value * (1 - discount_percent)

=======
            # Get applicable taxes for the product and map them using the website's FPOS
            product_taxes = product_or_template.sudo().taxes_id._filter_taxes_by_company(self.env.company)
            mapped_taxes = request.fiscal_position.map_tax(product_taxes)

            # Compute price per unit of product or template
            pricelist_prices = request.pricelist._compute_price_rule(product_or_template, quantity)
            unit_price = pricelist_prices[product_or_template.id][0]

            # Compute the tax-excluded value
            total_excluded_value = mapped_taxes.compute_all(
                price_unit=unit_price,
                currency=website.currency_id,
                product=product_or_template,
            )['total_excluded']

>>>>>>> 97ac892118f11ef511c7769dcfa97084b738e381
            # Store the tax-excluded price in the res for use in showing both prices
            combination_info['l10n_ar_price_tax_excluded'] = self._apply_taxes_to_price(
                combination_info['raw_pricelist_price'],
                website.currency_id,
                product_taxes=combination_info['product_taxes'],
                taxes=combination_info['taxes'],
                tax_display='total_excluded',
            )

        return combination_info
