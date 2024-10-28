/** @odoo-module **/

import { registry } from '@web/core/registry';

registry
    .category('web_tour.tours')
    .add('website_sale_product_configurator_shop_show_dialog', {
        url: '/shop?search=Main product',
        steps: () => [
            {
                content: "Click on the cart button",
                trigger: ".oe_product:has(a:contains(Main product))",
                run: "hover && click .oe_product:has(a:contains(Main product)) div.o_wsale_product_btn a",
            },
            {
                content: "Assert that the product configurator is shown",
                trigger: 'table.o_sale_product_configurator_table',
            },
        ],
   });
