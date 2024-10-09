/** @odoo-module **/

import { registry } from '@web/core/registry';
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_product_configurator_hide_dialog', {
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
            wsTourUtils.goToCart(),
            // Assert that the configurator wasn't shown.
            wsTourUtils.assertCartContains({ productName: "Main product"}),
        ],
   });
