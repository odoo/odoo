/** @odoo-module **/

import { registry } from "@web/core/registry";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('tour_shop_deleted_archived_variants', {
    url: '/shop?search=Test Product 2',
    steps: () => [
    {
        content: "check price on /shop (template price)",
        trigger: '.oe_product_cart .oe_currency_value:contains("1.00")',
        run: "click",
    },
    {
        content: "select Test Product 2",
        trigger: ".oe_product_cart a:contains(/^Test Product 2$/)",
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "check price (3rd variant)",
        trigger: '.oe_currency_value:contains("31.00")',
        run: "click",
    },
    {
        content: "click on the second variant",
        trigger: 'input[data-attribute_name="My Attribute"][data-value_name="My Value 2"]',
        run: "click",
    },
    {
        content: "check combination is not possible",
        trigger: '.js_main_product.css_not_available .css_not_available_msg:contains("This combination does not exist.")',
        run: "click",
    },
    {
        content: "click on the 3rd variant to reset the warning",
        trigger: 'input[data-attribute_name="My Attribute"][data-value_name="My Value 3"]',
        run: "click",
    },
    {
        content: "check price (3rd variant)",
        trigger: '.oe_currency_value:contains("31.00")',
        run: "click",
    },
    {
        content: "click on the first variant",
        trigger: 'input[data-attribute_name="My Attribute"][data-value_name="My Value 1"]',
        run: "click",
    },
    {
        content: "check combination is not possible",
        trigger: '.js_main_product.css_not_available .css_not_available_msg:contains("This combination does not exist.")',
        run: "click",
    },
    {
        content: "check add to cart not possible",
        trigger: '#add_to_cart.disabled',
    }
]});
