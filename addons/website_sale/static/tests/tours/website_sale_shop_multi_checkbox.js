/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('tour_shop_multi_checkbox', {
    url: '/shop?search=Product Multi',
    steps: () => [
    {
        content: "select Product",
        trigger: ".oe_product_cart a:text(Product Multi)",
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "check price",
        trigger: '.oe_currency_value:contains("750")',
    },
    {
        content: 'click on the first option to select it',
        trigger: 'input[data-attribute_name="Options"][data-value_name="Option 1"]',
        run: "click",
    },
    {
        content: 'click on the third option to select it',
        trigger: 'input[data-attribute_name="Options"][data-value_name="Option 3"]',
        run: "click",
    },
    {
        content: 'check combination is not possible',
        trigger: '.js_main_product.css_not_available .css_not_available_msg:contains("This combination does not exist.")',
        timeout: 30000,
        run: "click",
    },
    {
        content: "check add to cart not possible",
        trigger: '#add_to_cart.disabled',
    },
    {
        content: 'click on the third option to unselect it',
        trigger: 'input[data-attribute_name="Options"][data-value_name="Option 3"]',
        run: "click",
    },
    {
        content: 'click on the second option to select it',
        trigger: 'input[data-attribute_name="Options"][data-value_name="Option 2"]',
        run: "click",
    },
    {
        content: "check price of options is correct",
        trigger: '.oe_currency_value:contains("753")',
    },
    {
        content: "add to cart",
        trigger: 'a:contains(Add to cart)',
        run: "click",
    },
        tourUtils.goToCart(),
    {
        content: "check price is correct",
        trigger: '#cart_products div div.text-muted>span:contains("Options: Option 1, Option 2")',
    },
]});

registry.category("web_tour.tours").add('tour_shop_multi_checkbox_single_value', {
    url: '/shop?search=Burger',
    steps: () => [
    {
        content: "select Product",
        trigger: '.oe_product_cart a:text(Burger)',
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "check price",
        trigger: '.oe_currency_value:contains("750")',
    },
    {
        content: 'click on the first option to select it',
        trigger: 'input[data-attribute_name="Toppings"][data-value_name="cheese"]',
        run: "click",
    },
    {
        content: "check price of options is correct",
        trigger: '.oe_currency_value:contains("750")',
    },
    {
        content: "add to cart",
        trigger: 'a:contains(Add to cart)',
        run: "click",
    },
        tourUtils.goToCart(),
    {
        content: "check choice was correctly saved",
        trigger: '#cart_products div div.text-muted>span:contains("Toppings: cheese")',
    },
]});
