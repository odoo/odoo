/** @odoo-module **/

import { registry } from '@web/core/registry';
import configuratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_stock_product_configurator', {
        test: true,
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
            configuratorTourUtils.assertProductQuantity("Main product", 1),
            // Assert that it's impossible to add less than 1 product (only for the main product).
            configuratorTourUtils.setProductQuantity("Main product", 0),
            configuratorTourUtils.assertProductQuantity("Main product", 1),
            {
                content: "check that decrease button is disabled",
                trigger: `.modal button[name=sale_quantity_button_minus]:disabled`,
            },
            configuratorTourUtils.assertProductQuantity("Main product", 1),
            // Assert that it's impossible to add more products than available.
            configuratorTourUtils.setProductQuantity("Main product", 20),
            configuratorTourUtils.assertProductQuantity("Main product", 10),
            {
                content: "check that increase button is disabled",
                trigger: `.modal button[name=sale_quantity_button_plus]:disabled`,
            },
            configuratorTourUtils.assertProductQuantity("Main product", 10),
            {
                content: "Proceed to checkout",
                trigger: 'button:contains(Proceed to Checkout)',
                run: 'click',
            },
            {
                content: "Verify the quantity in the cart",
                trigger: 'div.o_cart_product input.quantity[value="10"]',
            },
        ],
   });
