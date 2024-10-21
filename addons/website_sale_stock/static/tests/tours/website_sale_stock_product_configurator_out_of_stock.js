/** @odoo-module **/

import { registry } from '@web/core/registry';
import configuratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';
import stockConfiguratorTourUtils from '@website_sale_stock/js/tours/product_configurator_tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_stock_product_configurator_out_of_stock', {
        url: '/shop?search=Main product',
        steps: () => [
            {
                content: "Select Main product",
                trigger: '.oe_product_cart a:contains("Main product")',
                run: 'click',
            },
            {
                content: "Click on add to cart",
                trigger: '#add_to_cart',
                run: 'click',
            },
            // Assert that the "Out of stock" variant of the optional product can't be sold.
            ...stockConfiguratorTourUtils.assertOptionalProductOutOfStock(
                "Optional product (Out of stock)"
            ),
            // Add the "Out of stock" variant by selecting the "In stock" variant, adding it, and
            // selecting the "Out of stock" variant again.
            configuratorTourUtils.selectAttribute("Optional product", "Stock", "In stock"),
            configuratorTourUtils.addOptionalProduct("Optional product (In stock)"),
            configuratorTourUtils.selectAttribute("Optional product", "Stock", "Out of stock"),
            // Assert that the "Out of stock" variant of the optional product still can't be sold.
            ...stockConfiguratorTourUtils.assertProductOutOfStock("Optional product (Out of stock)"),
            configuratorTourUtils.assertFooterButtonsDisabled(),
        ],
    });
