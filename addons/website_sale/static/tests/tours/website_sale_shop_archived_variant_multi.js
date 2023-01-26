/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('tour_shop_archived_variant_multi', {
    test: true,
    url: '/shop?search=Test Product 2',
    steps: [
    {
        content: "select Test Product",
        trigger: '.oe_product_cart a:containsExact("Test Product 2")',
    },
    {
        content: 'click on the first variant',
        trigger: 'input[data-attribute_name="Size"][data-value_name="Small"]',
    },
    {
        content: "click on the second variant",
        trigger: 'input[data-attribute_name="Color"][data-value_name="Black"]',
    },
    {
        content: "Check that brand b is not available and select it",
        trigger: '.css_not_available input[data-attribute_name="Brand"][data-value_name="Brand B"]',
    },
    {
        content: "check combination is not possible",
        trigger: '.js_main_product.css_not_available .css_not_available_msg:contains("This combination does not exist.")'
    },
    {
        content: "check add to cart not possible",
        trigger: '#add_to_cart.disabled',
        run: function () {},
    },
    {
        content: "change second variant to remove warning",
        trigger: 'input[data-attribute_name="Color"][data-value_name="White"]',
    },
    {
        content: "Check that second variant is disabled",
        trigger: '.css_not_available input[data-attribute_name="Color"][data-value_name="Black"]',
        run: function () {},
    },
]});
