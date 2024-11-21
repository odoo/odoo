/** @odoo-module **/

import { registry } from '@web/core/registry';

registry
    .category('web_tour.tours')
    .add('website_sale_product_configurator_show_dialog', {
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
            {
                content: "Assert that the product configurator is shown",
                trigger: 'table.o_sale_product_configurator_table',
            },
        ],
   });
