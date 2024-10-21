/** @odoo-module **/

import { registry } from '@web/core/registry';
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_product_configurator_shop_hide_dialog', {
        url: '/shop?search=Main product',
        steps: () => [
            {
                content: "Click on the cart button",
                trigger: '.oe_product:has(a:contains("Main product")) div.o_wsale_product_btn a',
                run: 'click',
            },
            wsTourUtils.goToCart(),
            // Assert that the configurator wasn't shown.
            wsTourUtils.assertCartContains({ productName: "Main product"}),
        ],
   });
