/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('tour_shop_multi_checkbox', {
    test: true,
    url: '/shop?search=Product Multi',
    steps: () => [
    {
        content: "select Product",
        trigger: '.oe_product_cart a:containsExact("Product Multi")',
    },
    {
        content: "check price",
        trigger: '.oe_currency_value:contains("750")',
        run: function () {},
    },
    {
        content: 'click on the first option to select it',
        trigger: 'input[data-attribute_name="Options"][data-value_name="Option 1"]',
    },
    {
        content: 'click on the third option to select it',
        trigger: 'input[data-attribute_name="Options"][data-value_name="Option 3"]',
    },
    {
        content: 'check combination is not possible',
        trigger: '.js_main_product.css_not_available .css_not_available_msg:contains("This combination does not exist.")'
    },
    {
        content: "check add to cart not possible",
        trigger: '#add_to_cart.disabled',
        run: function () {},
    },
    {
        content: 'click on the third option to unselect it',
        trigger: 'input[data-attribute_name="Options"][data-value_name="Option 3"]',
    },
    {
        content: 'click on the second option to select it',
        trigger: 'input[data-attribute_name="Options"][data-value_name="Option 2"]',
    },
    {
        content: "check price of options is correct",
        trigger: '.oe_currency_value:contains("753")',
        run: function () {},
    },
    {
        content: "add to cart",
        trigger: 'a:contains(ADD TO CART)',
    },
        tourUtils.goToCart(),
    {
        content: "check price is correct",
        trigger: '.td-product_name:contains("Options: Option 1, Option 2")',
        run: function () {},
    },
]});
