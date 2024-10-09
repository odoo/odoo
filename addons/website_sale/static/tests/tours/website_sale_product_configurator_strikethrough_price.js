/** @odoo-module **/

import { registry } from '@web/core/registry';
import configuratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';
import websiteConfiguratorTourUtils from '@website_sale/js/tours/product_configurator_tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_product_configurator_strikethrough_price', {
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
            configuratorTourUtils.assertProductPrice("Main product", '50.00'),
            websiteConfiguratorTourUtils.assertProductStrikethroughPrice("Main product", '100.00'),
            configuratorTourUtils.assertOptionalProductPrice("Optional product", '5.00'),
            websiteConfiguratorTourUtils.assertOptionalProductStrikethroughPrice(
                "Optional product", '10.00'
            ),
        ],
   });
