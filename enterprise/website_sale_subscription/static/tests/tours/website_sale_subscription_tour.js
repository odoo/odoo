/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('shop_buy_subscription_product', {
    url: '/shop',
    steps: () => [
        {
            content: "Search streaming write text",
            trigger: 'form input[name="search"]',
            run: "edit Streaming SUB Week",
        },
        {
            content: "Search streaming click",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Select streaming",
            trigger: '.oe_product_cart:first a:contains("Streaming SUB Weekly")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Add one quantity",
            trigger: '.css_quantity a.js_add_cart_json i.fa-plus',
            run: "click",
        },
        {
            content: "click on add to cart",
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
            run: "click",
        },
        {
            content: "See added to cart + try to add other recurrence",
            trigger: '.my_cart_quantity:contains("2")',
            run: function () {
                window.location.href = '/shop';
            },
            expectUnloadPage: true,
        },
        {
            content: "Search streaming monthly write text",
            trigger: 'form input[name="search"]',
            run: "edit Streaming SUB month",
        },
        {
            content: "Search streaming monthly click",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Select streaming monthly",
            trigger: '.oe_product_cart:first a:contains("Streaming SUB Monthly")',
            run: "click",
            expectUnloadPage: true,
        },
        wsTourUtils.goToCart({quantity: 2}),
        {
            content: 'Order overview page',
            trigger: 'h3:contains("Order overview")',
        },
    ]
});
