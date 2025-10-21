from odoo import models
from odoo.http import request


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_sales_prices(self, website):
        '''
        Resolution 4/2025 requires us to display both prices on the e-commerce site:
            - Price including taxes
            - Price excluding taxes

        If the website is configured to use tax-included pricing, we calculate the tax-excluded
        price separately. This tax-excluded price is displayed on the shop page (on both list and grid views).
        '''

        res = super()._get_sales_prices(website)
        fiscal_position_id = request.fiscal_position
        pricelist_prices = request.pricelist._compute_price_rule(self, 1.0)

        if (
            website
            and website.company_id.country_code == 'AR'
            and website.l10n_ar_website_sale_show_both_prices
            and website.show_line_subtotals_tax_selection == 'tax_included'
        ):
            for template_id, template_val in res.items():
                # Get applicable taxes for the product and map them using the website's FPOS
                template = self.env['product.template'].browse(template_id)
                product_taxes = template.sudo().taxes_id._filter_taxes_by_company(self.env.company)
                mapped_taxes = fiscal_position_id.map_tax(product_taxes)

                # Compute the tax-excluded value
                total_excluded_value = mapped_taxes.compute_all(
                    price_unit=pricelist_prices[template.id][0],
                    currency=website.currency_id,
                    product=template,
                )['total_excluded']

                # Store the tax-excluded price in the res for use in showing both prices
                res[template_id]['l10n_ar_price_tax_excluded'] = total_excluded_value

        return res

    def _get_additionnal_combination_info(self, product_or_template, quantity, uom, date, website):
        combination_info = super()._get_additionnal_combination_info(
            product_or_template, quantity, uom, date, website
        )
        if (
            website
            and website.company_id.country_code == 'AR'
            and website.l10n_ar_website_sale_show_both_prices
            and website.show_line_subtotals_tax_selection == 'tax_included'
        ):
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

            # Store the tax-excluded price in the res for use in showing both prices
            combination_info['l10n_ar_price_tax_excluded'] = total_excluded_value

        return combination_info
